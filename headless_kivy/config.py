# pyright: reportMissingImports=false
"""Implement `setup_headless_kivy`, it configures headless-kivy."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, NoReturn, NotRequired, Protocol, TypedDict

import kivy
import numpy as np
from kivy.config import Config
from kivy.metrics import dp

from headless_kivy.constants import (
    DOUBLE_BUFFERING,
    FLIP_HORIZONTAL,
    FLIP_VERTICAL,
    HEIGHT,
    IS_DEBUG_MODE,
    MAX_FPS,
    REGION_SIZE,
    ROTATION,
    WIDTH,
)
from headless_kivy.logger import add_file_handler, add_stdout_handler

if TYPE_CHECKING:
    from threading import Thread

    from numpy._typing import NDArray

kivy.require('2.1.0')


class SetupHeadlessConfig(TypedDict):
    """Arguments of `setup_headless_kivy` function.

    Attributes
    ----------
    callback: `Callback`
        The callback function that will render the data to the screen.
    max_fps: `int`, optional
        Maximum frames per second for the Kivy application.
    width: `int`, optional
        The width of the display in pixels.
    height: `int`, optional
        The height of the display in pixels.
    is_debug_mode: `bool`, optional
        If set to True, the application will consume computational resources to log
        additional debug information.
    double_buffering: `bool`, optional
        If set to True, it will let Kivy generate the next frame while sending the last
        frame to the display.
    rotation: `int`, optional
        The rotation of the display clockwise, it will be multiplied by 90.
    flip_horizontal: `bool`, optional
        Whether the screen should be flipped horizontally or not.
    flip_vertical: `bool`, optional
        Whether the screen should be flipped vertically or not.
    region_size: `int`, optional
        Approximate size of rectangles to divide the screen into and see if they need to
        be updated.

    """

    callback: Callback
    max_fps: NotRequired[int]
    width: NotRequired[int]
    height: NotRequired[int]
    is_debug_mode: NotRequired[bool]
    double_buffering: NotRequired[bool]
    rotation: NotRequired[int]
    flip_horizontal: NotRequired[bool]
    flip_vertical: NotRequired[bool]
    region_size: NotRequired[int]


_config: SetupHeadlessConfig | None = None


def report_uninitialized() -> NoReturn:
    """Report that the module has not been initialized."""
    msg = """You need to run `setup_headless_kivy` before importing \
`kivy.core.window` module. \
Note that it might have been imported by another module unintentionally."""
    raise RuntimeError(msg)


def setup_headless_kivy(config: SetupHeadlessConfig) -> None:
    """Configure the headless mode for the Kivy application.

    Arguments:
    ---------
    config: `SetupHeadlessConfig`

    """
    global _config  # noqa: PLW0603
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

    from headless_kivy.widget import HeadlessWidget

    HeadlessWidget.raw_data = np.zeros(
        (int(dp(height())), int(dp(width())), 4),
        dtype=np.uint8,
    )


def check_initialized() -> None:
    """Check if the module has been initialized."""
    if not _config:
        report_uninitialized()


class Region(TypedDict):
    """A region of the screen to be updated."""

    rectangle: tuple[int, int, int, int]
    data: NDArray[np.uint8]


class Callback(Protocol):
    """The signature of the renderer function."""

    def __call__(
        self: Callback,
        *,
        regions: list[Region],
        last_render_thread: Thread,
    ) -> None:
        """Render the data to the screen."""


@cache
def callback() -> Callback:
    """Return the render function, called whenever data is ready to be rendered."""
    if _config:
        return _config.get('callback', lambda **_: None)
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
def double_buffering() -> bool:
    """Generate the next frame while sending the last frame to the display."""
    if _config:
        return _config.get('double_buffering', DOUBLE_BUFFERING)
    report_uninitialized()


@cache
def rotation() -> int:
    """Return the rotation of the display."""
    if _config:
        return _config.get('rotation', ROTATION)
    report_uninitialized()


@cache
def flip_horizontal() -> bool:
    """Return `True` if the display is flipped horizontally."""
    if _config:
        return _config.get('flip_horizontal', FLIP_HORIZONTAL)
    report_uninitialized()


@cache
def flip_vertical() -> bool:
    """Return `True` if the display is flipped vertically."""
    if _config:
        return _config.get('flip_vertical', FLIP_VERTICAL)
    report_uninitialized()


@cache
def region_size() -> int:
    """Return the approximate size of rectangles to divide the screen into."""
    if _config:
        return _config.get('region_size', REGION_SIZE)
    report_uninitialized()
