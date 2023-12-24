# pyright: reportMissingImports=false
"""Implement `setup_kivy`, it configures Kivy."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, NotRequired, TypedDict

from kivy import Config

from headless_kivy_pi.constants import (
    AUTOMATIC_FPS_CONTROL,
    DEBUG_MODE,
    DOUBLE_BUFFERING,
    HEIGHT,
    IS_RPI,
    MAX_FPS,
    MIN_FPS,
    SYNCHRONOUS_CLOCK,
    WIDTH,
)
from headless_kivy_pi.fake import Fake
from headless_kivy_pi.logger import add_file_handler, add_stdout_handler

if TYPE_CHECKING:
    from adafruit_rgb_display.rgb import DisplaySPI

if not IS_RPI:
    sys.modules['board'] = Fake()
    sys.modules['digitalio'] = Fake()
    sys.modules['adafruit_rgb_display.st7789'] = Fake()


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


def setup_kivy(config: SetupHeadlessConfig) -> None:
    """Configure the headless mode for the Kivy application.

    Arguments:
    ---------
    config: `SetupHeadlessConfig`, optional
    """
    from headless_kivy_pi import HeadlessWidget

    if 'kivy.core.window' in sys.modules:
        msg = """You need to run `setup_headless` before importing \
`kivy.core.window` module. \
Note that it might have been imported by another module unintentionally."""
        raise RuntimeError(msg)

    min_fps = config.get('min_fps', MIN_FPS)
    max_fps = config.get('max_fps', MAX_FPS)
    width = config.get('width', WIDTH)
    height = config.get('height', HEIGHT)
    HeadlessWidget.debug_mode = config.get('debug_mode', DEBUG_MODE)
    HeadlessWidget.double_buffering = config.get(
        'double_buffering',
        DOUBLE_BUFFERING,
    )
    HeadlessWidget.synchronous_clock = config.get(
        'synchronous_clock',
        SYNCHRONOUS_CLOCK,
    )
    HeadlessWidget.automatic_fps_control = config.get(
        'automatic_fps',
        AUTOMATIC_FPS_CONTROL,
    )

    if HeadlessWidget.debug_mode:
        add_stdout_handler()
        add_file_handler()

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
