"""Utility functions for the project."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import numpy as np
from kivy.metrics import dp

from headless_kivy import config

if TYPE_CHECKING:
    from numpy._typing import NDArray


def divide_number(n: int) -> list[int]:
    """Divide a number into a list of smaller numbers."""
    k = round(n / config.region_size())
    base, rem = divmod(n, k)
    return [base + 1] * rem + [base] * (k - rem)


T = TypeVar('T')


def get(array: list[T], index: int) -> T | None:
    """Get an element from a list."""
    return next(iter(array[index : index + 1]), None)


def transform_data(data: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Apply transformations to the data."""
    data = np.rot90(data, config.rotation())
    if config.flip_horizontal():
        data = np.fliplr(data)
    if config.flip_vertical():
        data = np.flipud(data)
    return data


def transform_coordinates(
    region: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Transform the coordinates of a region."""
    y1, x1, y2, x2 = region[:4]
    h, w = int(dp(config.width())), int(dp(config.height()))
    positions = {
        0: (x1, y1, x2, y2),
        1: (y1, w - x2, y2, w - x1),
        2: (w - x2, h - y2, w - x1, h - y1),
        3: (h - y2, x1, h - y1, x2),
    }
    x1, y1, x2, y2 = positions[config.rotation() % 4]
    if config.flip_horizontal():
        if config.rotation() % 2 == 0:
            x1, x2 = w - x2, w - x1
        else:
            x1, x2 = h - x2, h - x1
    if config.flip_vertical():
        if config.rotation() % 2 == 0:
            y1, y2 = h - y2, h - y1
        else:
            y1, y2 = w - y2, w - y1
    return y1, x1, y2, x2


def divide_array_into_rectangles(
    array: np.ndarray,
) -> list[list[tuple[int, int, int, int]]]:
    """Divide a 2D array into multiple rectangles."""
    width_splits = divide_number(array.shape[0])
    height_splits = divide_number(array.shape[1])

    height_indices = np.cumsum([0, *height_splits])
    width_indices = np.cumsum([0, *width_splits])

    return [
        [
            (
                int(width_indices[j]),
                int(height_indices[i]),
                int(width_indices[j] + width_splits[j]),
                int(height_indices[i] + height_splits[i]),
            )
            for j in range(len(width_splits))
        ]
        for i in range(len(height_splits))
    ]


def divide_into_regions(
    mask: NDArray[np.bool_],
) -> list[tuple[int, int, int, int]]:
    """Divide a mask into regions."""
    blocks = [
        [
            block
            if np.any(
                mask[
                    block[0] : block[2],
                    block[1] : block[3],
                ],
            )
            else None
            for block in row
        ]
        for row in divide_array_into_rectangles(mask)
    ]
    remaining = [
        (column[0], row[0])
        for row in enumerate(blocks)
        for column in enumerate(row[1])
        if column[1] is not None
    ]
    regions: list[tuple[int, int, int, int]] = []
    while remaining:
        y, x = end_y, end_x = remaining[0]
        block = blocks[x][y]
        assert block is not None  # noqa: S101
        x1, y1, x2, y2 = block
        for i in range(x + 1, len(blocks)):
            candidate_block = blocks[i][y]
            if not candidate_block:
                break
            end_x = i
            y2 = candidate_block[3]

        for j in range(y + 1, len(blocks[0])):
            for i in range(x, end_x + 1):
                if not blocks[i][j]:
                    break
            else:
                end_y = j
                candidate_block = blocks[x][j]
                assert candidate_block is not None  # noqa: S101
                x2 = candidate_block[2]
                continue
            break
        remaining = [
            block
            for block in remaining
            if block[0] < y or block[1] < x or block[0] > end_y or block[1] > end_x
        ]
        for i in range(x, end_x + 1):
            for j in range(y, end_y + 1):
                blocks[i][j] = None
        regions.append((x1, y1, x2, y2))
    return regions
