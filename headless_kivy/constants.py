"""Provide constants of the package."""

import os

from str_to_bool import str_to_bool

BANDWIDTH_LIMIT = int(os.environ.get('HEADLESS_KIVY_BANDWIDTH_LIMIT', '0'))
BANDWIDTH_LIMIT_WINDOW = float(
    os.environ.get('HEADLESS_KIVY_BANDWIDTH_LIMIT_WINDOW', '1'),
)
BANDWIDTH_LIMIT_OVERHEAD = int(
    os.environ.get('HEADLESS_KIVY_BANDWIDTH_LIMIT_OVERHEAD', '0'),
)
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
