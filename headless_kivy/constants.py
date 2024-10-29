"""Provide constants of the package."""

import os

from str_to_bool import str_to_bool

MAX_FPS = int(os.environ.get('HEADLESS_KIVY_MAX_FPS', '32'))
WIDTH = int(os.environ.get('HEADLESS_KIVY_WIDTH', '240'))
HEIGHT = int(os.environ.get('HEADLESS_KIVY_HEIGHT', '240'))
IS_DEBUG_MODE = str_to_bool(os.environ.get('HEADLESS_KIVY_DEBUG', 'False')) == 1
DOUBLE_BUFFERING = (
    str_to_bool(
        os.environ.get('HEADLESS_KIVY_DOUBLE_BUFFERING', 'True'),
    )
    == 1
)
ROTATION = int(os.environ.get('HEADLESS_KIVY_ROTATION', '0'))
FLIP_HORIZONTAL = (
    str_to_bool(os.environ.get('HEADLESS_KIVY_FLIP_HORIZONTAL', 'False')) == 1
)
FLIP_VERTICAL = str_to_bool(os.environ.get('HEADLESS_KIVY_FLIP_VERTICAL', 'False')) == 1
REGION_SIZE = int(os.environ.get('HEADLESS_KIVY_REGION_SIZE', '60'))
