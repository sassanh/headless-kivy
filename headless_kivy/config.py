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
    HEIGHT,
    IS_DEBUG_MODE,
    WIDTH,
)
from headless_kivy.logger import add_file_handler, add_stdout_handler

if TYPE_CHECKING:
    from threading import Thread

    from numpy._typing import NDArray

kivy.require('2.1.0')


class SetupHeadlessConfig(TypedDict):
    """Arguments of `setup_headless_kivy` function."""

    """The callback function that will render the data to the screen."""
    callback: Callback
    """The width of the display in pixels."""
    width: NotRequired[int]
    """The height of the display in pixels."""
    height: NotRequired[int]
    """If set to True, the application will consume computational resources to log
    additional debug information."""
    is_debug_mode: NotRequired[bool]
    """Is set to `True`, it will let Kivy to generate the next frame while sending the
    last frame to the display."""
    double_buffering: NotRequired[bool]
    """The rotation of the display clockwise, it will be multiplied by 90."""
    rotation: NotRequired[int]
    """Whether the screen should be flipped horizontally or not"""
    flip_horizontal: NotRequired[bool]
    """Whether the screen should be flipped vertically or not"""
    flip_vertical: NotRequired[bool]


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

    Config.set('graphics', 'fbo', 'force-hardware')
    Config.set('graphics', 'width', f'{width()}')
    Config.set('graphics', 'height', f'{height()}')

    from headless_kivy import HeadlessWidget

    HeadlessWidget.raw_data = np.zeros(
        (int(dp(height())), int(dp(width())), 4)
        if rotation() % 2 == 0
        else (int(dp(width())), int(dp(height())), 4),
        dtype=np.uint8,
    )


def check_initialized() -> None:
    """Check if the module has been initialized."""
    if not _config:
        report_uninitialized()


class Callback(Protocol):
    """The signature of the renderer function."""

    def __call__(
        self: Callback,
        *,
        rectangle: tuple[int, int, int, int],
        data: NDArray[np.uint8],
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
