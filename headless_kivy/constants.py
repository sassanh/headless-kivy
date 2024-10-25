"""Provide constants of the package."""

import os

from str_to_bool import str_to_bool

WIDTH = int(os.environ.get('HEADLESS_KIVY_WIDTH', '240'))
HEIGHT = int(os.environ.get('HEADLESS_KIVY_HEIGHT', '240'))
IS_DEBUG_MODE = str_to_bool(os.environ.get('HEADLESS_KIVY_DEBUG', 'False')) == 1
DOUBLE_BUFFERING = (
    str_to_bool(
        os.environ.get('HEADLESS_KIVY_DOUBLE_BUFFERING', 'True'),
    )
    == 1
)
