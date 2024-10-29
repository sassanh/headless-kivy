"""Implement a Kivy widget that renders everything in memory.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.
"""

from __future__ import annotations

import time
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from kivy.graphics.context_instructions import Color
from kivy.graphics.fbo import Fbo
from kivy.graphics.gl_instructions import ClearBuffers, ClearColor
from kivy.graphics.instructions import Callback, Canvas
from kivy.graphics.vertex_instructions import Rectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget

from headless_kivy import config
from headless_kivy._debug import DebugMixin
from headless_kivy.utils import (
    divide_into_regions,
    transform_coordinates,
    transform_data,
)

if TYPE_CHECKING:
    from numpy._typing import NDArray


class HeadlessWidget(Widget, DebugMixin):
    """A Kivy widget that renders everything in memory."""

    fps = NumericProperty(0)

    update_region_seed = 0
    last_second: int
    rendered_frames: int
    skipped_frames: int

    last_render: float
    pending_render_threads: Queue[Thread]

    previous_data: NDArray[np.uint8] | None = None
    previous_frame: NDArray[np.uint8] | None = None
    fbo: Fbo
    fbo_background_color: Color
    fbo_background_rectangle: Rectangle

    fbo_render_color: Color
    fbo_render_rectangle: Rectangle

    raw_data: ClassVar[NDArray[np.uint8]]

    def __init__(self: HeadlessWidget, **kwargs: object) -> None:
        """Initialize a `HeadlessWidget`."""
        config.check_initialized()

        __import__('kivy.core.window')

        self.fps = config.max_fps()

        self.last_render = time.time()
        self.pending_render_threads = Queue(2 if config.double_buffering() else 1)

        self.canvas = Canvas()
        with self.canvas:
            self.fbo = Fbo(size=self.size, with_stencilbuffer=True)
            self.fbo_background_color = Color(0, 0, 0, 1)
            self.fbo_background_rectangle = Rectangle(size=self.size)
            self.fbo_render_color = Color(1, 1, 1, 1)
            if config.is_debug_mode():
                self.fbo_render_rectangle = Rectangle(
                    size=self.size,
                    texture=self.fbo.texture,
                )

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
        """Update size of fbo related elements when widget's size changes."""
        self.fbo.size = value
        self.fbo_background_rectangle.size = value
        if config.is_debug_mode():
            self.fbo_render_rectangle.size = value

    def on_pos(
        self: HeadlessWidget,
        _: HeadlessWidget,
        value: tuple[int, int],
    ) -> None:
        """Update position of fbo related elements when widget's position changes."""
        self.fbo_background_rectangle.pos = value
        if config.is_debug_mode():
            self.fbo_render_rectangle.pos = value

    def render_on_display(self: HeadlessWidget, *_: object) -> None:
        """Render the current frame on the display."""
        data = np.frombuffer(self.fbo.texture.pixels, dtype=np.uint8)
        if self.previous_data is not None and np.array_equal(data, self.previous_data):
            return
        self.last_render = time.time()
        self.previous_data = data
        # Render the current frame on the display asynchronously
        try:
            last_thread = self.pending_render_threads.get(False)
        except Empty:
            last_thread = None

        x, y = int(self.x), int(self.y)
        height = int(min(self.fbo.texture.height, dp(config.height()) - y))
        width = int(min(self.fbo.texture.width, dp(config.width()) - x))

        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0

        data = data.reshape(
            int(self.fbo.texture.height),
            int(self.fbo.texture.width),
            -1,
        )
        data = data[:height, :width, :]

        mask = np.any(data != self.previous_frame, axis=2)
        regions = divide_into_regions(mask)

        alpha_mask = np.repeat(mask[:, :, np.newaxis], 4, axis=2)
        self.previous_frame = data
        HeadlessWidget.raw_data[y : y + height, x : x + width, :][alpha_mask] = data[
            alpha_mask
        ]
        chunk = transform_data(
            HeadlessWidget.raw_data[y : y + height, x : x + width, :],
        )

        regions = [
            (*transform_coordinates(region[:4]), *region[4:]) for region in regions
        ]
        self.render_debug_info(
            (x, y, x + width, y + height),
            regions,
            chunk,
        )

        thread = Thread(
            target=config.callback(),
            kwargs={
                'regions': [
                    {
                        'rectangle': region[:4],
                        'data': chunk[
                            region[0] : region[2],
                            region[1] : region[3],
                            :,
                        ],
                    }
                    for region in regions
                ],
                'last_render_thread': last_thread,
            },
            daemon=False,
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
