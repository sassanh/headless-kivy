"""DebugMixin adds debug information to the HeadlessWidget class."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Self

from kivy.metrics import dp

from headless_kivy import config
from headless_kivy.logger import logger

if TYPE_CHECKING:
    import numpy as np
    from kivy.graphics.context_instructions import Color
    from kivy.graphics.fbo import Fbo
    from kivy.graphics.vertex_instructions import Rectangle
    from numpy._typing import NDArray


class DebugMixin:
    fbo: Fbo
    fbo_render_color: Color
    fbo_render_rectangle: Rectangle

    x: int
    y: int

    raw_data: ClassVar[NDArray[np.uint8]]

    def __init__(self: Self, **kwargs: dict[str, object]) -> None:
        super().__init__(**kwargs)
        if config.is_debug_mode():
            self.last_second = int(time.time())
            self.rendered_frames = 0
            self.skipped_frames = 0

    def set_debug_info(self: Self) -> None:
        # Log the number of skipped and rendered frames in the last second
        if config.is_debug_mode():
            self.fbo_render_rectangle.texture = self.fbo.texture
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

    def render_debug_info(
        self: Self,
        rect_: tuple[int, int, int, int],
        _: list[tuple[int, int, int, int]],
        data: NDArray[np.uint8],
    ) -> None:
        if config.is_debug_mode():
            x1, y1, x2, y2 = rect_
            self.rendered_frames += 1
            w = int(dp(config.width()))
            h = int(dp(config.height()))

            raw_file_path = Path('headless_kivy_buffer.raw')

            with raw_file_path.open('w+b') as file:
                file.truncate(w * h * 4)
                for i in range(y1, y2):
                    file.seek((x1 + i * w) * 4)
                    file.write(
                        bytes(self.raw_data[h - i - 1, x1:x2, :].flatten().tolist()),
                    )

            raw_file_path = Path(f'headless_kivy_buffer-{self.x}_{self.y}.raw')
            if config.rotation() % 2 != 0:
                w, h = h, w
                x1, y1, x2, y2 = y1, x1, y2, x2

            with raw_file_path.open('w+b') as file:
                file.truncate(w * h * 4)
                for i in range(y1, y2):
                    file.seek((x1 + i * w) * 4)
                    file.write(bytes(data[i - y1, x1:x2, :].flatten().tolist()))
