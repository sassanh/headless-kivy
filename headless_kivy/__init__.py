"""Headless widget useful for testing Kivy applications or driving embedded displays.

* IMPORTANT: You need to run `setup_headless` function before instantiating
`HeadlessWidget`.

A Kivy widget rendered in memory which doesn't create any window in any display manager
(a.k.a "headless").

It provides tooling for test environment and optimizations for custom displays in
embedded systems.

headless_kivy automatically throttles the frame rate to the value set by the `max_fps`
"""

from headless_kivy.widget import HeadlessWidget

__all__ = ('HeadlessWidget',)
