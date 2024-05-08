# pyright: reportMissingImports=false
"""Implement `setup_headless_kivy`, it configures headless-kivy-pi."""

from __future__ import annotations

import atexit
import sys
from functools import cache
from typing import TYPE_CHECKING, NoReturn, NotRequired, TypedDict

import kivy
import numpy as np
from kivy.config import Config

from headless_kivy_pi.constants import (
    AUTOMATIC_FPS,
    BAUDRATE,
    BITS_PER_BYTE,
    BYTES_PER_PIXEL,
    CLEAR_AT_EXIT,
    DOUBLE_BUFFERING,
    HEIGHT,
    IS_DEBUG_MODE,
    IS_RPI,
    MAX_FPS,
    MIN_FPS,
    SYNCHRONOUS_CLOCK,
    WIDTH,
)
from headless_kivy_pi.fake import Fake
from headless_kivy_pi.logger import add_file_handler, add_stdout_handler

if not IS_RPI:
    sys.modules['board'] = Fake()
    sys.modules['digitalio'] = Fake()
    sys.modules['adafruit_rgb_display.st7789'] = Fake()

import board
import digitalio
from adafruit_rgb_display.st7789 import ST7789

kivy.require('2.3.0')

if TYPE_CHECKING:
    from adafruit_rgb_display.rgb import DisplaySPI


class SetupHeadlessConfig(TypedDict):
    """Arguments of `setup_headless_kivy` function."""

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
    is_debug_mode: NotRequired[bool]
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
    clear_at_exit: NotRequired[bool]


_config: SetupHeadlessConfig | None = None
_display: DisplaySPI = None


def report_uninitialized() -> NoReturn:
    """Report that the module has not been initialized."""
    msg = """You need to run `setup_headless_kivy` before importing \
`kivy.core.window` module. \
Note that it might have been imported by another module unintentionally."""
    raise RuntimeError(msg)


def setup_headless_kivy(
    config: SetupHeadlessConfig,
    splash_screen: bytes | None = None,
) -> None:
    """Configure the headless mode for the Kivy application.

    Arguments:
    ---------
    config: `SetupHeadlessConfig`

    splash_screen: `bytes`
        it should have a length of `width` x `height` x 2

    """
    global _config, _display  # noqa: PLW0603
    _config = config

    if is_debug_mode():
        add_stdout_handler()
        add_file_handler()

    Config.set('kivy', 'kivy_clock', 'default')
    Config.set('graphics', 'fbo', 'force-hardware')
    Config.set('graphics', 'fullscreen', '0')
    Config.set('graphics', 'maxfps', f'{max_fps()}')
    Config.set('graphics', 'multisamples', '1')
    Config.set('graphics', 'resizable', '0')
    Config.set('graphics', 'vsync', '0')
    Config.set('graphics', 'width', f'{width()}')
    Config.set('graphics', 'height', f'{height()}')

    baudrate = config.get('baudrate', BAUDRATE)
    display_class: DisplaySPI = config.get('st7789', ST7789)
    clear_at_exit = config.get('clear_at_exit', CLEAR_AT_EXIT)

    if min_fps() > max_fps():
        msg = f"""Invalid value "{min_fps()}" for "min_fps", it can't \
be higher than 'max_fps' which is set to '{max_fps()}'."""
        raise ValueError(msg)

    fps_cap = baudrate / (width() * height() * BYTES_PER_PIXEL * BITS_PER_BYTE)

    if max_fps() > fps_cap:
        msg = f"""Invalid value "{max_fps()}" for "max_fps", it can't \
be higher than "{fps_cap:.1f}" (baudrate={baudrate} ÷ (width={width()} x \
height={height()} x bytes per pixel={BYTES_PER_PIXEL} x bits per byte=\
{BITS_PER_BYTE}))"""
        raise ValueError(msg)

    from kivy.metrics import dp

    if is_test_environment():
        Config.set('graphics', 'window_state', 'hidden')
        from kivy.core.window import Window

        _display = Fake()
    elif IS_RPI:
        Config.set('graphics', 'window_state', 'hidden')
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)
        spi = board.SPI()
        _display = display_class(
            spi,
            height=height(),
            width=width(),
            y_offset=80,
            x_offset=0,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=baudrate,
        )
        _display._block(  # noqa: SLF001
            0,
            0,
            width() - 1,
            height() - 1,
            bytes(width() * height() * 2) if splash_screen is None else splash_screen,
        )
        if clear_at_exit:
            atexit.register(
                lambda: _display
                and _display._block(  # noqa: SLF001
                    0,
                    0,
                    width() - 1,
                    height() - 1,
                    bytes(width() * height() * 2),
                ),
            )
    else:
        from kivy.core.window import Window
        from screeninfo import get_monitors

        monitor = get_monitors()[0]
        _display = Fake()

        Window._win.set_always_on_top(True)  # noqa: SLF001
        Window._set_top(200)  # noqa: SLF001
        Window._set_left(monitor.width - Window._size[0])  # noqa: SLF001

    _display.raw_data = np.zeros(
        (int(dp(width())), int(dp(height())), 3),
        dtype=np.uint8,
    )


def check_initialized() -> None:
    """Check if the module has been initialized."""
    if not _config:
        report_uninitialized()


@cache
def min_fps() -> int:
    """Return the minimum frames per second for when the Kivy application is idle."""
    if _config:
        return _config.get('min_fps', MIN_FPS)
    report_uninitialized()


@cache
def max_fps() -> int:
    """Return the maximum frames per second for the Kivy application."""
    if _config:
        return _config.get('max_fps', MAX_FPS)
    report_uninitialized()


@cache
def width() -> int:
    """Return the width of the display in pixels."""
    if _config:
        return _config.get('width', WIDTH)
    report_uninitialized()


@cache
def height() -> int:
    """Return the height of the display in pixels."""
    if _config:
        return _config.get('height', HEIGHT)
    report_uninitialized()


@cache
def is_debug_mode() -> bool:
    """Return `True` if the application will consume computational resources to log."""
    if _config:
        return _config.get('is_debug_mode', IS_DEBUG_MODE)
    report_uninitialized()


@cache
def is_test_environment() -> bool:
    """Return `True` if the application is running in test environment."""
    import os

    return 'PYTEST_CURRENT_TEST' in os.environ


@cache
def double_buffering() -> bool:
    """Generate the next frame while sending the last frame to the display."""
    if _config:
        return _config.get('double_buffering', DOUBLE_BUFFERING)
    report_uninitialized()


@cache
def synchronous_clock() -> bool:
    """headless-kivy-pi will wait for the LCD before rendering next frames."""
    if _config:
        return _config.get('synchronous_clock', SYNCHRONOUS_CLOCK)
    report_uninitialized()


@cache
def automatic_fps() -> bool:
    """headless-kivy-pi adjusts the FPS automatically."""
    if _config:
        return _config.get('automatic_fps', AUTOMATIC_FPS)
    report_uninitialized()


@cache
def rotation() -> int:
    """Return the rotation of the display."""
    if _config:
        return _config.get('rotation', 0)
    report_uninitialized()


@cache
def flip_horizontal() -> bool:
    """Return `True` if the display is flipped horizontally."""
    if _config:
        return _config.get('flip_horizontal', False)
    report_uninitialized()


@cache
def flip_vertical() -> bool:
    """Return `True` if the display is flipped vertically."""
    if _config:
        return _config.get('flip_vertical', False)
    report_uninitialized()


_is_paused: bool = False


def is_paused() -> bool:
    """Return `True` if rendering the application is paused."""
    return _is_paused


def pause() -> None:
    """Pause rendering the application."""
    global _is_paused  # noqa: PLW0603
    _is_paused = True


def resume() -> None:
    """Resume rendering the application."""
    global _is_paused  # noqa: PLW0603
    _is_paused = False
