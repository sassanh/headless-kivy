"""Implement a Kivy widget that renders everything in memory.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.

A Kivy widget rendered in memory which doesn't create any window in any display manager
(a.k.a "headless").

When no animation is running, you can drop fps to `min_fps` by calling
`activate_low_fps_mode`.

To increase fps to `max_fps` call `activate_high_fps_mode`.
"""

from __future__ import annotations

import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.context_instructions import Color
from kivy.graphics.fbo import Fbo
from kivy.graphics.gl_instructions import ClearBuffers, ClearColor
from kivy.graphics.vertex_instructions import Rectangle
from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from headless_kivy import config
from headless_kivy.logger import logger

if TYPE_CHECKING:
    from kivy.graphics.texture import Texture
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

    _is_setup_headless_called: bool = False
    should_ignore_hash: bool = False
    texture = ObjectProperty(None, allownone=True)

    last_second: int
    rendered_frames: int
    skipped_frames: int
    pending_render_threads: Queue[Thread]
    last_hash: int
    fps: int

    fbo: Fbo
    fbo_rect: Rectangle

    raw_data: NDArray[np.uint8]

    def __init__(self: HeadlessWidget, **kwargs: dict[str, object]) -> None:
        """Initialize a `HeadlessWidget`."""
        config.check_initialized()

        self.should_ignore_hash = False

        __import__('kivy.core.window')

        if config.is_debug_mode():
            self.last_second = int(time.time())
            self.rendered_frames = 0
            self.skipped_frames = 0

        self.pending_render_threads = Queue(2 if config.double_buffering() else 1)
        self.last_hash = 0
        self.last_change = time.time()
        self.fps = config.max_fps()

        self.canvas = self.fbo = Fbo(size=self.size, with_stencilbuffer=True)
        self.fbo_color = Color(1, 1, 1, 1)
        self.fbo_rect = Rectangle()

        with self.fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()

        self.texture = self.fbo.texture

        super().__init__(**kwargs)

        self.render_trigger = Clock.create_trigger(
            self.render_on_display,
            1 / self.fps,
            interval=True,
        )
        self.render_trigger()
        app = App.get_running_app()

        def clear(*_: object) -> None:
            self.render_trigger.cancel()

        if app:
            app.bind(on_stop=clear)

    def on_size(
        self: HeadlessWidget,
        _: HeadlessWidget,
        value: tuple[int, int],
    ) -> None:
        """Update size of `fbo` and size of `fbo_rect` when widget's size changes."""
        self.fbo.size = value
        self.texture = self.fbo.texture
        self.fbo_rect.size = value

    def on_pos(
        self: HeadlessWidget,
        _: HeadlessWidget,
        value: tuple[int, int],
    ) -> None:
        """Update position of `fbo_rect` when widget's position changes."""
        self.fbo_rect.pos = value

    def on_texture(self: HeadlessWidget, _: HeadlessWidget, value: Texture) -> None:
        """Update texture of `fbo_rect` when widget's texture changes."""
        self.fbo_rect.texture = value

    def on_alpha(self: HeadlessWidget, _: HeadlessWidget, value: float) -> None:
        """Update alpha value of `fbo_rect` when widget's alpha value changes."""
        self.fbo_color.rgba = (1, 1, 1, value)

    def render(self: HeadlessWidget) -> None:
        """Schedule a force render."""
        if not self:
            return
        Clock.schedule_once(self.render_on_display, 0)

    def _activate_high_fps_mode(self: HeadlessWidget) -> None:
        """Increase fps to `max_fps`."""
        if not self:
            return
        logger.info('Activating high fps mode, setting FPS to `max_fps`')
        self.fps = config.max_fps()
        self.render_trigger.timeout = 1.0 / self.fps
        self.last_hash = 0

    def activate_high_fps_mode(self: HeadlessWidget) -> None:
        """Schedule increasing fps to `max_fps`."""
        self.render()
        Clock.schedule_once(lambda _: self._activate_high_fps_mode(), 0)

    def _activate_low_fps_mode(self: HeadlessWidget) -> None:
        """Drop fps to `min_fps`."""
        logger.info('Activating low fps mode, dropping FPS to `min_fps`')
        self.fps = config.min_fps()
        self.render_trigger.timeout = 1.0 / self.fps

    def activate_low_fps_mode(self: HeadlessWidget) -> None:
        """Schedule dropping fps to `min_fps`."""
        self.render()
        Clock.schedule_once(lambda _: self._activate_low_fps_mode(), 0)

    def render_on_display(self: HeadlessWidget, *_: object) -> None:  # noqa: C901
        """Render the current frame on the display."""
        # Log the number of skipped and rendered frames in the last second
        if config.is_debug_mode():
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

        data = np.frombuffer(self.texture.pixels, dtype=np.uint8)
        data_hash = hash(data.data.tobytes())
        if data_hash == self.last_hash and not self.should_ignore_hash:
            # Only drop FPS when the screen has not changed for at least one second
            if (
                config.automatic_fps()
                and time.time() - self.last_change > 1
                and self.fps != config.min_fps()
            ):
                logger.debug('Frame content has not changed for 1 second')
                self.activate_low_fps_mode()

            # Considering the content has not changed, this frame can safely be ignored
            return

        self.should_ignore_hash = False

        self.last_change = time.time()
        self.last_hash = data_hash
        if config.automatic_fps() and self.fps != config.max_fps():
            logger.debug('Frame content has changed')
            self.activate_high_fps_mode()

        # Render the current frame on the display asynchronously
        try:
            last_thread = self.pending_render_threads.get(False)
        except Empty:
            last_thread = None

        height = int(min(self.texture.height, dp(config.height()) - self.y))
        width = int(min(self.texture.width, dp(config.width()) - self.x))

        data = data.reshape(int(self.texture.height), int(self.texture.width), -1)
        data = data[:height, :width, :]
        data = apply_tranformations(data)
        x, y = int(self.x), int(dp(config.height()) - self.y - self.height)

        if config.is_debug_mode():
            self.rendered_frames += 1
            raw_file_path = Path('headless_kivy_buffer.raw')

            if not raw_file_path.exists():
                with raw_file_path.open('wb') as file:
                    file.write(
                        b'\x00' * int(dp(config.width()) * dp(config.height()) * 4),
                    )
            with raw_file_path.open('r+b') as file:
                for i in range(height):
                    file.seek(int((x + (y + i) * dp(config.width())) * 4))
                    file.write(bytes(data[i, :, :].flatten().tolist()))

        if config.rotation() % 2 == 0:
            HeadlessWidget.raw_data[y : y + height, x : x + width, :] = data
        else:
            HeadlessWidget.raw_data[x : x + width, y : y + height, :] = data

        thread = Thread(
            target=config.callback(),
            kwargs={
                'rectangle': (x, y, x + width - 1, y + height - 1),
                'data': data,
                'data_hash': data_hash,
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
