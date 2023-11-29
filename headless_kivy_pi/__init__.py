"""Implement a Kivy widget that renders everything to SPI display while being headless.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.

A Kivy widget that renders itself on a display connected to the SPI controller of RPi.
It doesn't create any window in any display manager (a.k.a "headless").

When no animation is running, you can drop fps to `min_fps` by calling
`activate_low_fps_mode`.

To increase fps to `max_fps` call `activate_high_fps_mode`.
"""
from __future__ import annotations

import atexit
import os
import time
from distutils.util import strtobool
from pathlib import Path
from queue import Queue
from threading import Semaphore, Thread
from typing import TYPE_CHECKING, ClassVar

import kivy
import numpy as np
from kivy.app import ObjectProperty, Widget
from kivy.clock import Clock
from kivy.config import Config
from kivy.graphics import (
    Canvas,
    ClearBuffers,
    ClearColor,
    Color,
    Fbo,
    Rectangle,
)
from typing_extensions import Any, NotRequired, TypedDict

from headless_kivy_pi.logger import add_file_handler, add_stdout_handler, logger

if TYPE_CHECKING:
    from kivy.graphics.texture import Texture
    from numpy._typing import NDArray

kivy.require('2.2.1')

# Check if the code is running on a Raspberry Pi
IS_RPI = Path('/etc/rpi-issue').exists()
DisplaySPI: type
ST7789: type
if IS_RPI:
    import board
    import digitalio
    from adafruit_rgb_display.rgb import DisplaySPI as _DisplaySPI
    from adafruit_rgb_display.st7789 import ST7789 as _ST7789

    ST7789 = _ST7789
    DisplaySPI = _DisplaySPI
else:
    DisplaySPI = type('DisplaySPI', (), {})
    ST7789 = type('ST7789', (DisplaySPI,), {})

# Constants for calculations
BYTES_PER_PIXEL = 2
BITS_PER_BYTE = 11

# Configure the headless mode for the Kivy application and initialize the display

MIN_FPS = int(os.environ.get('HEADLESS_KIVY_PI_MIN_FPS', '1'))
MAX_FPS = int(os.environ.get('HEADLESS_KIVY_PI_MAX_FPS', '30'))
WIDTH = int(os.environ.get('HEADLESS_KIVY_PI_WIDTH', '240'))
HEIGHT = int(os.environ.get('HEADLESS_KIVY_PI_HEIGHT', '240'))
BAUDRATE = int(os.environ.get('HEADLESS_KIVY_PI_BAUDRATE', '60000000'))
DEBUG_MODE = (
    strtobool(
        os.environ.get('HEADLESS_KIVY_PI_DEBUG', 'False' if IS_RPI else 'True'),
    )
    == 1
)
DOUBLE_BUFFERING = (
    strtobool(
        os.environ.get('HEADLESS_KIVY_PI_DOUBLE_BUFFERING', 'True'),
    )
    == 1
)
SYNCHRONOUS_CLOCK = (
    strtobool(
        os.environ.get('HEADLESS_KIVY_PI_SYNCHRONOUS_CLOCK', 'True'),
    )
    == 1
)
AUTOMATIC_FPS_CONTROL = (
    strtobool(
        os.environ.get('HEADLESS_KIVY_PI_AUTOMATIC_FPS_CONTROL', 'False'),
    )
    == 1
)
CLEAR_AT_EXIT = (
    strtobool(os.environ.get('HEADLESS_KIVY_PI_CLEAR_AT_EXIT', 'False')) == 1
)


class SetupHeadlessConfig(TypedDict):
    """Arguments of `setup_headless` function."""

    """Minimum frames per second for when the Kivy application is idle."""
    min_fps: NotRequired[int]
    """Maximum frames per second for the Kivy application."""
    max_fps: NotRequired[int]
    """The width of the display in pixels."""
    width: NotRequired[int]
    """The height of the display in pixels."""
    height: NotRequired[int]
    """The baud rate for the display connection."""
    baudrate: NotRequired[int]
    """If set to True, the application will consume computational resources to log
    additional debug information."""
    debug_mode: NotRequired[bool]
    """The display class to use (default is ST7789)."""
    display_class: NotRequired[type[DisplaySPI]]
    """Is set to `True`, it will let Kivy generate the next frame while sending the
    last frame to the display."""
    double_buffering: NotRequired[bool]
    """If set to `True`, Kivy will wait for the LCD before rendering next frames. This
    will cause Headless to skip frames if they are rendered before the LCD has finished
    displaying the previous frames. If set to False, frames will be rendered
    asynchronously, letting Kivy render frames regardless of display being able to catch
    up or not at the expense of possible frame skipping."""
    synchronous_clock: NotRequired[bool]
    """If set to `True`, it will monitor the hash of the screen data, if this hash
    changes, it will increase the fps to the maximum and if the hash doesn't change for
    a while, it will drop the fps to the minimum."""
    automatic_fps: NotRequired[bool]
    """If set to `True`, it will clear the screen before exiting."""
    clear_at_eixt: NotRequired[bool]


def setup_headless(config: SetupHeadlessConfig | None = None) -> None:
    """Configure the headless mode for the Kivy application.

    Arguments:
    ---------
    config: `SetupHeadlessConfig`, optional
    """
    if config is None:
        config = {}

    min_fps = config.get('min_fps', MIN_FPS)
    max_fps = config.get('max_fps', MAX_FPS)
    width = config.get('width', WIDTH)
    height = config.get('height', HEIGHT)
    baudrate = config.get('baudrate', BAUDRATE)
    HeadlessWidget.debug_mode = config.get('debug_mode', DEBUG_MODE)
    display_class: DisplaySPI = config.get('st7789', ST7789)
    HeadlessWidget.double_buffering = config.get('double_buffering', DOUBLE_BUFFERING)
    HeadlessWidget.synchronous_clock = config.get(
        'synchronous_clock',
        SYNCHRONOUS_CLOCK,
    )
    HeadlessWidget.automatic_fps_control = config.get(
        'automatic_fps',
        AUTOMATIC_FPS_CONTROL,
    )
    clear_at_exit = config.get('clear_at_exit', CLEAR_AT_EXIT)

    if HeadlessWidget.debug_mode:
        add_stdout_handler()
        add_file_handler()

    if min_fps > max_fps:
        msg = f"""Invalid value "{min_fps}" for "min_fps", it can't be higher than \
'max_fps' which is set to '{max_fps}'."""
        raise ValueError(msg)

    fps_cap = baudrate / (width * height * BYTES_PER_PIXEL * BITS_PER_BYTE)

    if max_fps > fps_cap:
        msg = f"""Invalid value "{max_fps}" for "max_fps", it can't be higher than \
"{fps_cap:.1f}" (baudrate={baudrate} ÷ (width={width} x height={height} x bytes per \
pixel={BYTES_PER_PIXEL} x bits per byte={BITS_PER_BYTE}))"""
        raise ValueError(
            msg,
        )

    HeadlessWidget.min_fps = min_fps
    HeadlessWidget.max_fps = max_fps
    HeadlessWidget.width = width
    HeadlessWidget.height = height

    HeadlessWidget.is_paused = False

    Config.set('kivy', 'kivy_clock', 'default')
    Config.set('graphics', 'fbo', 'force-hardware')
    Config.set('graphics', 'fullscreen', '0')
    Config.set('graphics', 'maxfps', f'{max_fps}')
    Config.set('graphics', 'multisamples', '1')
    Config.set('graphics', 'resizable', '0')
    Config.set('graphics', 'vsync', '0')
    Config.set('graphics', 'width', f'{width}')
    Config.set('graphics', 'height', f'{height}')

    if IS_RPI:
        Config.set('graphics', 'window_state', 'hidden')
        spi = board.SPI()
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)
        display = display_class(
            spi,
            height=height,
            width=width,
            y_offset=80,
            x_offset=0,
            rotation=180,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=baudrate,
        )
        HeadlessWidget._display = display
        if clear_at_exit:
            atexit.register(
                lambda: display._block(
                    0,
                    0,
                    width - 1,
                    height - 1,
                    bytes(width * height * 2),
                ),
            )
    else:
        from kivy.core.window import Window
        from screeninfo import get_monitors

        monitor = get_monitors()[0]

        Window._win.set_always_on_top(True)  # noqa: SLF001
        Window._set_top(200)  # noqa: SLF001
        Window._set_left(monitor.width - Window._size[0])  # noqa: SLF001


class HeadlessWidget(Widget):
    """Headless Kivy widget class rendering on SPI connected display."""

    should_ignore_hash: ClassVar = False
    texture = ObjectProperty(None, allownone=True)
    _display: DisplaySPI

    min_fps: int
    max_fps: int
    is_paused: bool
    width: int
    height: int
    debug_mode: bool
    double_buffering: bool
    synchronous_clock: bool
    automatic_fps_control: bool

    last_second: int
    rendered_frames: int
    skipped_frames: int
    pending_render_threads: Queue[Thread]
    last_hash: int
    fps_control_queue = Semaphore(1)
    fps: int
    latest_release_thread: Thread | None = None

    fbo: Fbo
    fbo_rect: Rectangle

    def __init__(self: HeadlessWidget, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize a `HeadlessWidget`."""
        if HeadlessWidget.width is None or HeadlessWidget.height is None:
            msg = '"setup_headless" should be called before instantiating "Headless"'
            raise RuntimeError(msg)
        if self.debug_mode:
            self.last_second = int(time.time())
            self.rendered_frames = 0
            self.skipped_frames = 0

        self.pending_render_threads = Queue(2 if HeadlessWidget.double_buffering else 1)
        self.last_hash = 0
        self.last_change = time.time()
        self.fps = self.max_fps

        self.canvas = Canvas()
        with self.canvas:
            self.fbo = Fbo(size=self.size, with_stencilbuffer=True)
            self.fbo_color = Color(1, 1, 1, 1)
            self.fbo_rect = Rectangle()

        with self.fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()

        self.texture = self.fbo.texture

        super().__init__(**kwargs)

        self.render_on_display_event = Clock.create_trigger(
            self.render_on_display,
            0,
            True,
        )
        self.render_on_display_event()

    def add_widget(
        self: HeadlessWidget,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Extend `Widget.add_widget` and handle `canvas`."""
        canvas = self.canvas
        self.canvas = self.fbo
        super().add_widget(*args, **kwargs)
        self.canvas = canvas

    def remove_widget(
        self: HeadlessWidget,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Extend `Widget.remove_widget` and handle `canvas`."""
        canvas = self.canvas
        self.canvas = self.fbo
        super().remove_widget(*args, **kwargs)
        self.canvas = canvas

    def on_size(
        self: HeadlessWidget,
        _: HeadlessWidget,
        value: tuple[int, int],
    ) -> None:
        """Update size of `fbo` and size of `fbo_rect` when widget's size changes."""
        self.fbo.size = value
        self.texture = self.fbo.texture
        self.fbo_rect.size = value

    def on_pos(
        self: HeadlessWidget,
        _: HeadlessWidget,
        value: tuple[int, int],
    ) -> None:
        """Update position of `fbo_rect` when widget's position changes."""
        self.fbo_rect.pos = value

    def on_texture(self: HeadlessWidget, _: HeadlessWidget, value: Texture) -> None:
        """Update texture of `fbo_rect` when widget's texture changes."""
        self.fbo_rect.texture = value

    def on_alpha(self: HeadlessWidget, _: HeadlessWidget, value: float) -> None:
        """Update alpha value of `fbo_rect` when widget's alpha value changes."""
        self.fbo_color.rgba = (1, 1, 1, value)

    def release_frame(self: HeadlessWidget) -> None:
        """Schedule dequeuing `fps_control_queue` to allow rendering the next frame.

        It runs a new thread, its job will be solely wait until its time to render the
        next frame and then dequeue the `fps_control_queue`.
        The waiting time is calculated based on the current fps.
        """

        def release_task() -> None:
            time.sleep(1 / self.fps)
            HeadlessWidget.fps_control_queue.release()

        self.latest_release_thread = Thread(target=release_task)
        self.latest_release_thread.start()

    @classmethod
    def pause(cls: type[HeadlessWidget]) -> None:
        """Pause writing to the display."""
        HeadlessWidget.is_paused = True

    @classmethod
    def resume(cls: type[HeadlessWidget]) -> None:
        """Resume writing to the display."""
        cls.is_paused = False
        cls.should_ignore_hash = True
        cls.reset_fps_control_queue()

    @classmethod
    def reset_fps_control_queue(cls: type[HeadlessWidget]) -> None:
        """Dequeue `fps_control_queue` forcfully to render the next frame.

        It is required in case `release_task` is waiting for the next frame based on
        previous fps and now fps is increased and we don't want to wait that long.
        """

        def task() -> None:
            cls.fps_control_queue.release()
            if cls.latest_release_thread:
                cls.latest_release_thread.join()
            cls.fps_control_queue.acquire()

        Thread(target=task).start()

    @classmethod
    def activate_high_fps_mode(cls: type[HeadlessWidget]) -> None:
        """Increase fps to `max_fps`."""
        logger.info('Activating high fps mode, setting FPS to `max_fps`')
        cls.fps = cls.max_fps
        cls.reset_fps_control_queue()

    @classmethod
    def _activate_low_fps_mode(cls: type[HeadlessWidget], *_: object) -> None:
        logger.info('Activating low fps mode, dropping FPS to `min_fps`')
        cls.fps = cls.min_fps

    @classmethod
    def activate_low_fps_mode(cls: type[HeadlessWidget]) -> None:
        """Drop fps to `min_fps`."""
        Clock.schedule_once(cls._activate_low_fps_mode)

    def transfer_to_display(
        self: HeadlessWidget,
        data: NDArray[np.uint16],
        data_hash: int,
        last_render_thread: Thread,
    ) -> None:
        """Transfer data to the display via SPI controller."""
        logger.debug(f'Rendering frame with hash "{data_hash}"')

        # Flip the image vertically
        data = data[::-1, :, :3].astype(np.uint16)

        color = (
            ((data[:, :, 0] & 0xF8) << 8)
            | ((data[:, :, 1] & 0xFC) << 3)
            | (data[:, :, 2] >> 3)
        )
        data_bytes = bytes(
            np.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist(),
        )

        # Wait for the last render thread to finish
        if last_render_thread:
            last_render_thread.join()

        # Only render when running on a Raspberry Pi
        if IS_RPI and not HeadlessWidget.is_paused:
            HeadlessWidget._display._block(
                0,
                0,
                HeadlessWidget.width - 1,
                HeadlessWidget.height - 1,
                data_bytes,
            )

    def render_on_display(self: HeadlessWidget, *_: Any) -> None:  # noqa: ANN401
        """Render the widget on display connected to the SPI controller."""
        # Block if it is rendering more FPS than expected
        HeadlessWidget.fps_control_queue.acquire()
        self.release_frame()

        # Log the number of skipped and rendered frames in the last second
        if self.debug_mode:
            # Increment rendered_frames/skipped_frames count every frame and reset their
            # values to zero every second.
            current_second = int(time.time())

            if current_second != self.last_second:
                logger.debug(
                    f"""Frames in {self.last_second}: \
    [Skipped: {self.skipped_frames}] [Rendered: {self.rendered_frames}]""",
                )
                self.last_second = current_second
                self.rendered_frames = 0
                self.skipped_frames = 0

        # If `synchronous_clock` is False, skip frames if there are more than one
        # pending render in case `double_buffering` is enabled, or if there are ANY
        # pending render in case `double_buffering` is disabled.
        if (
            not HeadlessWidget.synchronous_clock
            and self.pending_render_threads.qsize()
            > (1 if HeadlessWidget.double_buffering else 0)
        ):
            self.skipped_frames += 1
            return

        if self.debug_mode:
            self.rendered_frames += 1

        data = np.frombuffer(self.texture.pixels, dtype=np.uint8).reshape(
            HeadlessWidget.width,
            HeadlessWidget.height,
            -1,
        )
        data_hash = hash(data.data.tobytes())
        if data_hash == self.last_hash and not HeadlessWidget.should_ignore_hash:
            # Only drop FPS when the screen has not changed for at least one second
            if (
                self.automatic_fps_control
                and time.time() - self.last_change > 1
                and self.fps != self.min_fps
            ):
                logger.debug('Frame content has not changed for 1 second')
                self.activate_low_fps_mode()

            # Considering the content has not changed, this frame can safely be ignored
            return

        HeadlessWidget.should_ignore_hash = False

        self.last_change = time.time()
        self.last_hash = data_hash
        if self.automatic_fps_control and self.fps != self.max_fps:
            logger.debug('Frame content has changed')
            self.activate_high_fps_mode()

        # Render the current frame on the display asynchronously
        thread = Thread(
            target=self.transfer_to_display,
            args=(
                data,
                data_hash,
                self.pending_render_threads.get()
                if self.pending_render_threads.qsize() > 0
                else None,
            ),
        )
        self.pending_render_threads.put(thread)
        thread.start()
