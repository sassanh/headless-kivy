"""Implement `transfer_to_display` function."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from headless_kivy_pi.constants import IS_RPI
from headless_kivy_pi.logger import logger

if TYPE_CHECKING:
    from threading import Thread

    from numpy._typing import NDArray


def transfer_to_display(
    data: NDArray[np.uint16],
    data_hash: int,
    last_render_thread: Thread,
) -> None:
    """Transfer data to the display via SPI controller."""
    from headless_kivy_pi import HeadlessWidget

    logger.debug(f'Rendering frame with hash "{data_hash}"')

    # Flip the image vertically
    data = data.reshape(
        HeadlessWidget.width,
        HeadlessWidget.height,
        -1,
    )[::-1, :, :3].astype(np.uint16)

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
    if IS_RPI:
        HeadlessWidget._display._block(  # noqa: SLF001
            0,
            0,
            HeadlessWidget.width - 1,
            HeadlessWidget.height - 1,
            data_bytes,
        )
