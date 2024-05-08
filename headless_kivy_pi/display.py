"""Implement `transfer_to_display` function."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from headless_kivy_pi import config
from headless_kivy_pi.logger import logger

if TYPE_CHECKING:
    from threading import Thread

    from numpy._typing import NDArray


def transfer_to_display(
    rectangle: tuple[int, int, int, int],
    data: NDArray[np.uint16],
    data_hash: int,
    last_render_thread: Thread,
) -> None:
    """Transfer data to the display via SPI controller."""
    logger.debug(f'Rendering frame with hash "{data_hash}"')

    data = data.reshape(rectangle[2], rectangle[3], -1)[:, :, :3].astype(np.uint16)
    data = np.rot90(data, config.rotation())
    if config.flip_horizontal():
        data = np.fliplr(data)
    if config.flip_vertical():
        data = np.flipud(data)

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
    display = config._display  # noqa: SLF001
    if display:
        display.raw_data[rectangle[0] : rectangle[0] + rectangle[2]][
            rectangle[1] : rectangle[1] + rectangle[3]
        ] = data
        display._block(*rectangle, data_bytes)  # noqa: SLF001
