"""Implement a Kivy widget that renders everything in memory.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.
"""

from __future__ import annotations

import contextlib
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from queue import Empty, Queue
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from kivy.clock import Clock
from kivy.graphics.context_instructions import Color
from kivy.graphics.fbo import Fbo
from kivy.graphics.gl_instructions import ClearBuffers, ClearColor
from kivy.graphics.instructions import Callback, Canvas
from kivy.graphics.vertex_instructions import Rectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget

from headless_kivy import config, logger
from headless_kivy._debug import DebugMixin
from headless_kivy.utils import (
    divide_into_regions,
    transform_coordinates,
    transform_data,
)

if TYPE_CHECKING:
    from kivy._clock import ClockEvent
    from numpy._typing import NDArray  # pyright: ignore[reportPrivateImportUsage]


class HeadlessWidget(Widget, DebugMixin):
    """A Kivy widget that renders everything in memory."""

    fps: int = NumericProperty(24)

    update_region_seed = 0
    last_second: int
    rendered_frames: int
    skipped_frames: int

    last_render: float
    scheduler: ClockEvent | None = None
    render_queue: Queue[Future]

    previous_frame: NDArray[np.uint8] | None = None
    fbo: Fbo
    fbo_background_color: Color
    fbo_background_rectangle: Rectangle

    fbo_render_color: Color
    fbo_render_rectangle: Rectangle

    raw_data: ClassVar[NDArray[np.uint8]]
    transfer_record: ClassVar[dict[float, int]] = {}

    def __init__(self: HeadlessWidget, **kwargs: object) -> None:
        """Initialize a `HeadlessWidget`."""
        config.check_initialized()

        __import__('kivy.core.window')

        self.thread_pool = ThreadPoolExecutor(
            max_workers=2 if config.double_buffering() else 1,
        )
        self.thread_lock = threading.Lock()
        self.last_render_task: Future | None = None
        self.last_render = 0
        self.render_queue = Queue(2 if config.double_buffering() else 1)

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
            Callback(self.process_frame)

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

    def process_frame(self: HeadlessWidget, *_: object) -> None:
        """Process the frame and render it on the display."""
        self.set_debug_info()

        if self.scheduler and self.scheduler.is_triggered:
            self.scheduler.cancel()
            if config.is_debug_mode():
                self.skipped_frames += 1

        now = time.time()
        if now - self.last_render < 1 / self.fps or self.render_queue.qsize() > (
            1 if config.double_buffering() else 0
        ):
            self.scheduler = Clock.schedule_once(
                self.process_frame,
                1 / self.fps,
            )
            return

        data = np.frombuffer(self.fbo.texture.pixels, dtype=np.uint8).reshape(
            int(self.fbo.texture.height),
            int(self.fbo.texture.width),
            -1,
        )

        x, y = max(int(self.x), 0), max(int(self.y), 0)
        height = int(min(self.fbo.texture.height, dp(config.height()) - y))
        width = int(min(self.fbo.texture.width, dp(config.width()) - x))

        data = data[:height, :width, :]

        mask = np.any(data != self.previous_frame, axis=2)
        self.previous_frame = data.copy()
        if not np.any(mask):
            return

        with self.thread_lock:
            future = self.thread_pool.submit(
                self.render,
                mask=mask,
                data=data,
                x=x,
                y=y,
                last_render_task=self.last_render_task,
            )
            self.last_render_task = future
            self.render_queue.put(future)
        self.last_render = time.time()

    def render(
        self: HeadlessWidget,
        *,
        mask: NDArray[np.bool_],
        data: NDArray[np.uint8],
        x: int,
        y: int,
        last_render_task: Future | None = None,
    ) -> None:
        """Render the current frame."""
        height = data.shape[0]
        width = data.shape[1]

        regions = divide_into_regions(mask)

        if config.bandwidth_limit() != 0:
            while True:
                now = time.time()
                size = sum(
                    [
                        (region[2] - region[0]) * (region[3] - region[1])
                        + config.bandwidth_limit_overhead()
                        for region in regions
                    ],
                )
                HeadlessWidget.transfer_record = {
                    time: size
                    for time, size in HeadlessWidget.transfer_record.items()
                    if time > now - config.bandwidth_limit_window()
                }
                if (
                    sum(HeadlessWidget.transfer_record.values()) + size
                    > config.bandwidth_limit() * config.bandwidth_limit_window()
                ):
                    logger.logger.debug(
                        f"""postponing due to bandwidth limit, new pixels: {
                            size
                        } - limit: {
                            config.bandwidth_limit() * config.bandwidth_limit_window()
                        }""",
                    )
                    time.sleep(
                        max(
                            min(HeadlessWidget.transfer_record.keys())
                            - (time.time() - config.bandwidth_limit_window()),
                            0,
                        ),
                    )
                    continue
                break
            HeadlessWidget.transfer_record[now] = size

        alpha_mask = np.repeat(mask[:, :, np.newaxis], 4, axis=2)

        if last_render_task:
            last_render_task.result()

        HeadlessWidget.raw_data[y : y + height, x : x + width, :][alpha_mask] = data[
            alpha_mask
        ]

        chunk = transform_data(
            HeadlessWidget.raw_data[y : y + height, x : x + width, :].copy(),
        )
        regions = [transform_coordinates(region) for region in regions]

        self.render_debug_info(
            (x, y, x + width, y + height),
            regions,
            chunk,
        )

        config.callback()(
            regions=[
                {
                    'rectangle': region,
                    'data': chunk[
                        region[0] : region[2],
                        region[1] : region[3],
                        :,
                    ],
                }
                for region in regions
            ],
        )
        with contextlib.suppress(Empty):
            self.render_queue.get_nowait()

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
