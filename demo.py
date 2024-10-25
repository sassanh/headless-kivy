# ruff: noqa: E402
"""Demonstrate the usage of the HeadlessWidget class."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import TYPE_CHECKING

import png

from headless_kivy import HeadlessWidget, config

if TYPE_CHECKING:
    from threading import Thread

    import numpy as np
    from numpy._typing import NDArray

WIDTH = 400
HEIGHT = 240


def render(
    *,
    rectangle: tuple[int, int, int, int],
    data: NDArray[np.uint8],
    last_render_thread: Thread,
) -> None:
    """Render the data to a png file."""
    _ = rectangle, last_render_thread
    with Path('demo.png').open('wb') as file:
        png.Writer(
            alpha=True,
            width=data.shape[1],
            height=data.shape[0],
            greyscale=False,  # pyright: ignore [reportArgumentType]
            bitdepth=8,
        ).write(
            file,
            data.reshape(-1, data.shape[1] * 4).tolist(),
        )


config.setup_headless_kivy(
    {
        'callback': render,
        'width': WIDTH,
        'height': HEIGHT,
        'flip_vertical': True,
        'rotation': 1,
    },
)

from kivy.app import App
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label


class FboGridLayout(GridLayout, HeadlessWidget):
    """The `HeadlessWidget` subclass for the `GridLayout` class."""


class DemoApp(App):
    """The demo application class."""

    def build(self) -> FboGridLayout:
        """Build the demo application."""
        fbg = FboGridLayout(rows=2, cols=2)

        for index, color in enumerate(
            [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 0)],
        ):
            label = Label(text=f'Hello {index}')

            def render(
                label: Label,
                *_: object,
                color: tuple[float, float, float, float],
            ) -> None:
                with label.canvas.before:
                    Color(*color)
                    Rectangle(pos=label.pos, size=label.size)

            label.bind(
                size=functools.partial(render, color=color),
                pos=functools.partial(render, color=color),
            )

            fbg.add_widget(label)
        return fbg


if __name__ == '__main__':
    DemoApp().run()
