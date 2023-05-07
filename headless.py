import os
import time
from distutils.util import strtobool
from pathlib import Path
from queue import Queue
from threading import Semaphore, Thread
from typing import Type

import kivy
from adafruit_rgb_display.rgb import DisplaySPI, numpy
from kivy.app import ObjectProperty, Widget
from kivy.base import Clock
from kivy.config import Config
from kivy.graphics import Canvas, ClearBuffers, ClearColor, Color, Fbo, Rectangle

from logger import add_file_handler, add_stdout_handler, logger

kivy.require("2.2.0")

# Check if the code is running on a Raspberry Pi
IS_RPI = Path("/etc/rpi-issue").exists()
ST7789: Type[DisplaySPI]
if IS_RPI:
    import board
    import digitalio
    from adafruit_rgb_display.st7789 import ST7789
else:
    ST7789 = type("ST7789", (DisplaySPI,), {})

# Constants for calculations
BYTES_PER_PIXEL = 2
BITS_PER_BYTE = 11

# Configure the headless mode for the Kivy application and initialize the display


def setup_headless(
    min_fps: int = int(os.environ.get("HEADLESS_KIVY_PI_MIN_FPS", "1")),
    max_fps: int = int(os.environ.get("HEADLESS_KIVY_PI_MAX_FPS", "20")),
    width: int = int(os.environ.get("HEADLESS_KIVY_PI_WIDTH", "240")),
    height: int = int(os.environ.get("HEADLESS_KIVY_PI_HEIGHT", "240")),
    baudrate: int = int(os.environ.get("HEADLESS_KIVY_PI_BAUDRATE", "96000000")),
    debug_mode: bool = strtobool(
        os.environ.get("HEADLESS_KIVY_PI_DEBUG", "False" if IS_RPI else "True")
    )
    == 1,
    display_class: Type[DisplaySPI] = ST7789,
    double_buffering: bool = strtobool(
        os.environ.get("HEADLESS_KIVY_PI_DOUBLE_BUFFERING", "True")
    )
    == 1,
    synchronous_clock: bool = strtobool(
        os.environ.get("HEADLESS_KIVY_PI_SYNCHRONOUS_CLOCK", "True")
    )
    == 1,
):
    """
    Configures the headless mode for the Kivy application.

    :param min_fps: Minimum frames per second for when the Kivy application is idle.
    :param max_fps: Maximum frames per second for the Kivy application.
    :param width: The width of the display in pixels.
    :param height: The height of the display in pixels.
    :param baudrate: The baud rate for the display connection.
    :param debug_mode: If set to True, the application will consume computational \
resources to log additional debug information.
    :param display_class: The display class to use (default is ST7789).
    :param double_buffering: Is set to `True`, it will let Kivy generate the next \
frame while sending the last frame to the display.
    :param synchronous_clock: If set to True, Kivy will wait for the LCD before \
rendering next frames. This will cause Headless to skip frames if they are rendered \
before the LCD has finished displaying the previous frames. If set to False, frames \
will be rendered asynchronously, letting Kivy render frames regardless of display \
being able to catch up or not at the expense of possible frame skipping.
    """
    if debug_mode:
        add_stdout_handler()
        add_file_handler()

    if min_fps > max_fps:
        raise ValueError(
            f"""Invalid value "{min_fps}" for "min_fps", it can't be higher than \
"max_fps" which is set to "{max_fps}"."""
        )

    fps_cap = baudrate / (width * height * BYTES_PER_PIXEL * BITS_PER_BYTE)

    logger.info(f"Theoretically possible FPS based on baudrate: {fps_cap:.1f}")

    if max_fps > fps_cap:
        raise ValueError(
            f"""Invalid value "{max_fps}" for "max_fps", it can't be higher than \
"{fps_cap:.1f}" (baudrate={baudrate} ÷ (width={width} x height={height} x \
bytes per pixel={BYTES_PER_PIXEL} x bits per byte={BITS_PER_BYTE}))"""
        )

    Headless.min_fps = min_fps
    Headless.max_fps = max_fps
    Headless.width = width
    Headless.height = height
    Headless.debug_mode = debug_mode
    Headless.double_buffering = double_buffering
    Headless.synchronous_clock = synchronous_clock

    Config.set("kivy", "kivy_clock", "default")
    Config.set("graphics", "fbo", "force-hardware")
    Config.set("graphics", "fullscreen", "0")
    Config.set("graphics", "maxfps", f"{max_fps}")
    Config.set("graphics", "multisamples", "1")
    Config.set("graphics", "resizable", "0")
    Config.set("graphics", "vsync", "0")
    Config.set("graphics", "width", f"{width}")
    Config.set("graphics", "height", f"{height}")

    if IS_RPI:
        Config.set("graphics", "window_state", "hidden")
        spi = board.SPI()
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)
        global display
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
    else:
        from kivy.core.window import Window
        from screeninfo import get_monitors

        monitor = get_monitors()[0]

        Window._win.set_always_on_top(True)
        Window._set_top(0)
        Window._set_left(monitor.width - Window._size[0])


# Headless Kivy widget class rendering on SPI display
class Headless(Widget):
    texture = ObjectProperty(None, allownone=True)

    min_fps: int
    max_fps: int
    width: int
    height: int
    debug_mode: bool
    double_buffering: bool
    synchronous_clock: bool

    last_second: int
    rendered_frames: int
    skipped_frames: int
    pending_render_threads: Queue[Thread]
    last_hash: int
    fps_control_queue: Semaphore
    fps: int
    latest_release_thread: Thread

    def __init__(self, **kwargs):
        if Headless.width is None or Headless.height is None:
            raise Exception(
                '"setup_headless" should be called before instantiating "Headless"'
            )
        super(Headless, self).__init__(**kwargs)
        if self.debug_mode:
            self.last_second = int(time.time())
            self.rendered_frames = 0
            self.skipped_frames = 0

        self.pending_render_threads = Queue(2 if Headless.double_buffering else 1)
        self.last_hash = 0
        self.last_change = time.time()
        self.fps_control_queue = Semaphore(1)
        self.fps = self.max_fps

        self.canvas = Canvas()
        with self.canvas:
            self.fbo = Fbo(size=self.size)
            self.fbo_color = Color(1, 1, 1, 1)
            self.fbo_rect = Rectangle()

        with self.fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()

        self.texture = self.fbo.texture

        self.render_on_display_event = Clock.create_trigger(
            self.render_on_display, 0, True
        )
        self.render_on_display_event()

    def add_widget(self, *args, **kwargs):
        canvas = self.canvas
        self.canvas = self.fbo
        ret = super(Headless, self).add_widget(*args, **kwargs)
        self.canvas = canvas
        return ret

    def remove_widget(self, *args, **kwargs):
        canvas = self.canvas
        self.canvas = self.fbo
        super(Headless, self).remove_widget(*args, **kwargs)
        self.canvas = canvas

    def on_size(self, _, value):
        self.fbo.size = value
        self.texture = self.fbo.texture
        self.fbo_rect.size = value

    def on_pos(self, _, value):
        self.fbo_rect.pos = value

    def on_texture(self, _, value):
        self.fbo_rect.texture = value

    def on_alpha(self, _, value):
        self.fbo_color.rgba = (1, 1, 1, value)

    def release_frame_task(self):
        time.sleep(1 / self.fps)
        self.fps_control_queue.release()

    def release_frame(self):
        self.latest_release_thread = Thread(target=self.release_frame_task)
        self.latest_release_thread.start()

    def reset_fps_control_queue(self):
        def task():
            self.fps_control_queue.release()
            self.latest_release_thread.join()
            self.fps_control_queue.acquire()

        Thread(target=task).start()

    def render_on_display(self, *_):
        if self.debug_mode:
            logger.debug(f"FPS: {Clock.get_fps():.1f}")
        # Block if it is rendering more FPS than expected
        self.fps_control_queue.acquire()
        self.release_frame()

        # Log the number of skipped and rendered frames in the last second
        if self.debug_mode:
            # Increment rendered_frames/skipped_frames count every frame and reset their
            # values to zero every second.
            current_second = int(time.time())

            if current_second != self.last_second:
                logger.debug(
                    f"""Frames in {self.last_second}: \
    [Skipped: {self.skipped_frames}] [Rendered: {self.rendered_frames}]"""
                )
                self.last_second = current_second
                self.rendered_frames = 0
                self.skipped_frames = 0

        # If `synchronous_clock` is False, skip frames if there are more than one
        # pending render in case `double_buffering` is enabled, or if there are ANY
        # pending render in case `double_buffering` is disabled.
        if not Headless.synchronous_clock:
            if self.pending_render_threads.qsize() > (
                1 if Headless.double_buffering else 0
            ):
                self.skipped_frames += 1
                return

        if self.debug_mode:
            self.rendered_frames += 1

        def render_task(data, last_render_thread):
            logger.debug(f'Rendering frame with hash "{data_hash}"')

            color = (
                ((data[:, :, 0] & 0xF8) << 8)
                | ((data[:, :, 1] & 0xFC) << 3)
                | (data[:, :, 2] >> 3)
            )
            data = bytes(
                numpy.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()
            )

            # Wait for the last render thread to finish
            if last_render_thread:
                last_render_thread.join()

            # Only render when running on a Raspberry Pi
            if IS_RPI:
                display._block(0, 0, Headless.width - 1, Headless.height - 1, data)

        data = numpy.frombuffer(self.texture.pixels, dtype=numpy.uint8).reshape(
            Headless.width, Headless.height, -1
        )
        data = data[:, :, :3].astype(numpy.uint16)
        data_hash = hash(data.data.tobytes())
        if data_hash == self.last_hash:
            # Only drop FPS when the screen has not changed for at least one second
            if time.time() - self.last_change > 1 and self.fps != self.min_fps:
                logger.debug(
                    """Frame content has not changed for 1 second, dropping FPS to \
`min_fps`"""
                )
                self.fps = self.min_fps

            # Considering the content has not changed, this frame can safely be considered rendered
            return
        else:
            self.last_change = time.time()
            self.last_hash = data_hash
            if self.fps != self.max_fps:
                logger.debug("Frame content has changed, setting FPS to `max_fps`")
                self.fps = self.max_fps
                self.reset_fps_control_queue()

        # Render the current frame on the display asynchronously
        thread = Thread(
            target=render_task,
            args=(
                data,
                self.pending_render_threads.get()
                if self.pending_render_threads.qsize() > 0
                else None,
            ),
        )
        self.pending_render_threads.put(thread)
        thread.start()
