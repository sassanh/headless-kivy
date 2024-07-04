"""Pytest plugin for headless-kivy."""

import pytest


@pytest.hookimpl
def pytest_addoption(parser: pytest.Parser) -> None:
    """Add options to the pytest command line."""
    group = parser.getgroup('headless-kivy', 'headless kivy options')
    group.addoption('--override-window-snapshots', action='store_true')
    group.addoption('--make-screenshots', action='store_true')
