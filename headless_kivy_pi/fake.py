"""Implementation of a `Fake` `ModuleType` class.

To be used to fake RPi modules not available in development machines.
"""
from __future__ import annotations

from types import ModuleType

from headless_kivy_pi.logger import logger


class Fake(ModuleType):
    """Fake a module or a class."""

    def __init__(self: Fake) -> None:
        """Fake constructor."""
        super().__init__('')

    def __getattr__(self: Fake, attr: str) -> Fake:
        """Fake all attrs."""
        logger.debug(
            'Accessing fake attribute of a `Fake` instance',
            extra={'attr': attr},
        )
        return Fake()

    def __call__(self: Fake, *args: object, **kwargs: object) -> Fake:
        """Fake call."""
        logger.debug(
            'Calling a `Fake` instance',
            extra={'args': args, 'kwargs': kwargs},
        )
        return Fake()
