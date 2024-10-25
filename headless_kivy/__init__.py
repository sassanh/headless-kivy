"""Implement a Kivy widget that renders everything in memory.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.

A Kivy widget rendered in memory which doesn't create any window in any display manager
(a.k.a "headless").
"""

from __future__ import annotations

import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from kivy.graphics.fbo import Fbo
from kivy.graphics.gl_instructions import ClearBuffers, ClearColor
from kivy.graphics.instructions import Callback, Canvas
from kivy.graphics.vertex_instructions import Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget

from headless_kivy import config
from headless_kivy.logger import logger

if TYPE_CHECKING:
    from numpy._typing import NDArray


def apply_tranformations(data: NDArray[np.uint8]) -> NDArray[np.uint8]:
    data = np.rot90(data, config.rotation())
    if config.flip_horizontal():
        data = np.fliplr(data)
    if config.flip_vertical():
        data = np.flipud(data)
    return data


class HeadlessWidget(Widget):
    """A Kivy widget that renders everything in memory."""

    last_second: int
    rendered_frames: int
    skipped_frames: int
    pending_render_threads: Queue[Thread]

    previous_data: NDArray[np.uint8] | None = None
    previous_frame: NDArray[np.uint8] | None = None
    fbo: Fbo
    fbo_rectangle: Rectangle

    raw_data: ClassVar[NDArray[np.uint8]]

    def __init__(self: HeadlessWidget, **kwargs: dict[str, object]) -> None:
        """Initialize a `HeadlessWidget`."""
        config.check_initialized()

        __import__('kivy.core.window')

        if config.is_debug_mode():
            self.last_second = int(time.time())
            self.rendered_frames = 0
            self.skipped_frames = 0

        self.pending_render_threads = Queue(2 if config.double_buffering() else 1)
        self.canvas = Canvas()

        with self.canvas:
            self.fbo = Fbo(size=self.size, with_stencilbuffer=True)
            if config.is_debug_mode():
                self.fbo_rectangle = Rectangle(size=self.size, texture=self.fbo.texture)

        with self.fbo.before:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()

        with self.fbo.after:
            Callback(self.render_on_display)

        super().__init__(**kwargs)

    def add_widget(
        self: HeadlessWidget,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Extend `Widget.add_widget` and handle `canvas`."""
        canvas = self.canvas
        self.canvas = self.fbo
        super().add_widget(*args, **kwargs)
        self.canvas = canvas

    def remove_widget(
        self: HeadlessWidget,
        *args: object,
        **kwargs: object,
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
        if config.is_debug_mode():
            self.fbo_rectangle.size = value

    def on_pos(
        self: HeadlessWidget,
        _: HeadlessWidget,
        value: tuple[int, int],
    ) -> None:
        """Update position of `fbo_rect` when widget's position changes."""
        if config.is_debug_mode():
            self.fbo_rectangle.pos = value

    def render_on_display(self: HeadlessWidget, *_: object) -> None:  # noqa: C901
        """Render the current frame on the display."""
        # Log the number of skipped and rendered frames in the last second
        if config.is_debug_mode():
            self.fbo_rectangle.texture = self.fbo.texture
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

        data = np.frombuffer(self.fbo.texture.pixels, dtype=np.uint8)
        if self.previous_data is not None and np.array_equal(data, self.previous_data):
            if config.is_debug_mode():
                self.skipped_frames += 1
            return
        self.previous_data = data
        # Render the current frame on the display asynchronously
        try:
            last_thread = self.pending_render_threads.get(False)
        except Empty:
            last_thread = None

        height = int(min(self.fbo.texture.height, dp(config.height()) - self.y))
        width = int(min(self.fbo.texture.width, dp(config.width()) - self.x))

        data = data.reshape(
            int(self.fbo.texture.height),
            int(self.fbo.texture.width),
            -1,
        )
        data = data[:height, :width, :]
        data = apply_tranformations(data)
        x, y = int(self.x), int(dp(config.height()) - self.y - self.height)

        mask = np.any(data != self.previous_frame, axis=2)
        alpha_mask = np.repeat(mask[:, :, np.newaxis], 4, axis=2)
        self.previous_frame = data
        if config.rotation() % 2 == 0:
            HeadlessWidget.raw_data[y : y + height, x : x + width, :][alpha_mask] = (
                data[alpha_mask]
            )
        else:
            HeadlessWidget.raw_data[x : x + width, y : y + height, :][alpha_mask] = (
                data[alpha_mask]
            )

        if config.is_debug_mode():
            self.rendered_frames += 1
            raw_file_path = Path(f'headless_kivy_buffer-{self.x}_{self.y}.raw')

            if not raw_file_path.exists():
                with raw_file_path.open('wb') as file:
                    file.write(
                        b'\x00' * int(dp(config.width()) * dp(config.height()) * 4),
                    )
            with raw_file_path.open('r+b') as file:
                for i in range(height):
                    file.seek(int((x + (y + i) * dp(config.width())) * 4))
                    file.write(bytes(data[i, :, :].flatten().tolist()))

            raw_file_path = Path('headless_kivy_buffer.raw')

            if not raw_file_path.exists():
                with raw_file_path.open('wb') as file:
                    file.write(
                        b'\x00' * int(dp(config.width()) * dp(config.height()) * 4),
                    )
            with raw_file_path.open('r+b') as file:
                for i in range(height):
                    file.seek(int((x + (y + i) * dp(config.width())) * 4))
                    file.write(
                        bytes(
                            HeadlessWidget.raw_data[y + i, x : x + width, :]
                            .flatten()
                            .tolist(),
                        ),
                    )

        thread = Thread(
            target=config.callback(),
            kwargs={
                'rectangle': (x, y, x + width - 1, y + height - 1),
                'data': data,
                'last_render_thread': last_thread,
            },
            daemon=True,
        )
        self.pending_render_threads.put(thread)
        thread.start()

    @classmethod
    def get_instance(
        cls: type[HeadlessWidget],
        widget: Widget,
    ) -> HeadlessWidget | None:
        """Get the nearest instance of `HeadlessWidget`."""
        if isinstance(widget, HeadlessWidget):
            return widget
        if widget.parent:
            return cls.get_instance(widget.parent)
        return None


__all__ = ['HeadlessWidget']
