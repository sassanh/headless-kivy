# ruff: noqa: E402
"""Demonstrate the usage of the HeadlessWidget class."""

from __future__ import annotations

from pathlib import Path

import png

from headless_kivy import HeadlessWidget, config

WIDTH = 400
HEIGHT = 240


def render(
    *,
    regions: list[config.Region],
) -> None:
    """Render the data to a png file."""
    data = regions[0]['data']
    with Path('demo.png').open('wb') as file:
        png.Writer(
            alpha=True,
            width=data.shape[1],
            height=data.shape[0],
            greyscale=False,  # pyright: ignore [reportArgumentType]
            bitdepth=8,
        ).write(
            file,
            data.reshape(data.shape[0], -1).tolist(),
        )


config.setup_headless_kivy(
    {
        'callback': render,
        'width': WIDTH,
        'height': HEIGHT,
        'flip_vertical': True,
        'rotation': 3,
    },
)

from kivy.app import App
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Ellipse
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label


class FboGridLayout(GridLayout, HeadlessWidget):
    """The `HeadlessWidget` subclass for the `GridLayout` class."""


class DemoApp(App):
    """The demo application class."""

    def build(self) -> FboGridLayout:
        """Build the demo application."""
        fbg = FboGridLayout(rows=2, cols=2)

        shape_by_label = {}
        for index, color in enumerate(
            [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 0)],
        ):
            label = Label(text=f'Hello {index}')

            with label.canvas.before:
                Color(*color)
                shape_by_label[label] = Ellipse()

            label.bind(
                size=lambda label, *_: (
                    setattr(
                        shape_by_label[label],
                        'size',
                        (label.size[0] / 2, label.size[1] / 2),
                    ),
                    setattr(
                        shape_by_label[label],
                        'pos',
                        (
                            label.pos[0] + label.size[0] / 4,
                            label.pos[1] + label.size[1] / 4,
                        ),
                    ),
                ),
                pos=lambda label, *_: setattr(
                    shape_by_label[label],
                    'pos',
                    (
                        label.pos[0] + label.size[0] / 4,
                        label.pos[1] + label.size[1] / 4,
                    ),
                ),
            )

            fbg.add_widget(label)
        return fbg


if __name__ == '__main__':
    DemoApp().run()
