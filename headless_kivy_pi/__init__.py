# pyright: reportMissingImports=false
"""Implement a Kivy widget that renders everything to SPI display while being headless.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.

A Kivy widget that renders itself on a display connected to the SPI controller of RPi.
It doesn't create any window in any display manager (a.k.a "headless").

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
from kivy.graphics.instructions import Canvas
from kivy.graphics.vertex_instructions import Rectangle
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from headless_kivy_pi import config
from headless_kivy_pi.display import transfer_to_display
from headless_kivy_pi.logger import logger

if TYPE_CHECKING:
    from adafruit_rgb_display.rgb import DisplaySPI
    from kivy.graphics.texture import Texture


class HeadlessWidget(Widget):
    """Headless Kivy widget class rendering on SPI connected display."""

    _is_setup_headless_called: bool = False
    should_ignore_hash: bool = False
    texture = ObjectProperty(None, allownone=True)
    _display: DisplaySPI

    last_second: int
    rendered_frames: int
    skipped_frames: int
    pending_render_threads: Queue[Thread]
    last_hash: int
    fps: int

    fbo: Fbo
    fbo_rect: Rectangle

    def __init__(self: HeadlessWidget, **kwargs: dict[str, object]) -> None:
        """Initialize a `HeadlessWidget`."""
        if not config.is_test_environment():
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

        self.canvas = Canvas()
        with self.canvas:
            self.fbo = Fbo(size=self.size, with_stencilbuffer=True)
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

    def render_on_display(self: HeadlessWidget, *_: object) -> None:
        """Render the widget on display connected to the SPI controller."""
        if config.is_paused():
            return

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

        # If `synchronous_clock` is False, skip frames if there are more than one
        # pending render in case `double_buffering` is enabled, or if there are ANY
        # pending render in case `double_buffering` is disabled.
        if not config.synchronous_clock() and self.pending_render_threads.qsize() > (
            1 if config.double_buffering() else 0
        ):
            self.skipped_frames += 1
            return

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

        if config.is_debug_mode():
            self.rendered_frames += 1
            with Path('headless_kivy_pi_buffer.raw').open('wb') as snapshot_file:
                snapshot_file.write(
                    bytes(
                        data.reshape(
                            config.width(),
                            config.height(),
                            -1,
                        )[::-1, :, :3]
                        .flatten()
                        .tolist(),
                    ),
                )

        self.should_ignore_hash = False

        self.last_change = time.time()
        self.last_hash = data_hash
        if config.automatic_fps and self.fps != config.max_fps():
            logger.debug('Frame content has changed')
            self.activate_high_fps_mode()

        # Render the current frame on the display asynchronously
        try:
            last_thread = self.pending_render_threads.get(False)
        except Empty:
            last_thread = None
        thread = Thread(
            target=transfer_to_display,
            args=(
                (self.x, self.y, self.width, self.height),
                data,
                data_hash,
                last_thread,
            ),
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
