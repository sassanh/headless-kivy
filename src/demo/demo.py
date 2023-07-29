"""Implement a paginated menu.

The first page starts with a title.
Each item may have sub items, in that case activating this item will open a new menu
with its sub items.
Each item can optionally be styled differently.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from typing_extensions import Any, NotRequired, TypedDict

from src.headless.headless import HeadlessWidget, setup_headless

os.environ['KIVY_METRICS_DENSITY']= '1'
os.environ['KIVY_NO_CONFIG'] = '1'
os.environ['KIVY_NO_FILELOG'] = '1'

setup_headless()

from kivy.app import App, Widget  # noqa: I001,E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import (ColorProperty, ListProperty,  # noqa: E402
                              StringProperty)
from kivy.uix.screenmanager import Screen, ScreenManager  # noqa: E402


if TYPE_CHECKING:
    from collections.abc import Iterator

class Menu(TypedDict):
    """A class used to represent a menu.

    Attributes
    ----------
    title: str
        The title of the menu shown on all pages.

    heading: str
        Rendered in the first page of the menu, stating the purpose of the menu and its
    items.

    sub_heading: str
        Rendered beneath the heading in the first page of the menu with a smaller font.

    items: List[Item]
        List of the items of the menu
    """

    title: str
    heading: str
    sub_heading: str
    items: list[Item]

class Item(TypedDict):
    """A class used to represent a menu item.

    Attributes
    ----------
    label: `str`
        The label of the item.

    color: `tuple` of `float`
        The color in rgba format as a list of floats, the list should contain 4
    elements: red, green, blue and alpha, each being a number in the range [0..1].
    For example (0.5, 0, 0.5, 0.8) represents a semi transparent purple.

    sub_menu: `Menu`, optional
        If provided, activating this item will open another menu, the description
        described in this field.
    """

    label: str
    color: NotRequired[tuple[float, float, float, float]]
    sub_menu: NotRequired[Menu]

PAGE_SIZE = 3
MAIN_MENU: Menu = {
    'title': 'Hello world',
    'heading': 'Please choose an item',
    'sub_heading': 'This is sub heading',
    'items': [
        {
            'label': 'First Item',
            'sub_menu': {
                'title': 'Sub menu',
                'heading': 'Please choose an item',
                'sub_heading': 'This is sub heading',
                'items': [
                    {
                        'label': 'Back',
                    },
                ],
            },
        },
        {
            'label': 'Second Item',
            'color': (1, 0, 1, 1),
        },
        {
            'label': 'Third Item',
        },
        {
            'label': 'Fourth Item',
        },
    ],
}

def paginate(items: list[Item]) -> Iterator[list[Item]]:
    """Yield successive PAGE_SIZE-sized chunks from list."""
    for i in range(0, len(items), PAGE_SIZE):
        yield items[i:i + PAGE_SIZE]

class ItemWidget(Widget):
    """Renders an `Item`."""

    color = ColorProperty((1, 1, 1, 1))
    label = StringProperty()
    sub_menu = None

class PageWidget(Screen):
    """renders a page of a `Menu`."""

    items = ListProperty([])

    def __init__(
        self: PageWidget,
        items: list[Item],
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize a `MenuWidget`.

        Arguments:
        ---------
        items: `list` of `Item`
            The items to be shown in this page

        kwargs: Any
            Stuff that will get directly passed to the `__init__` method of Kivy's
        `Screen`.
        """
        super().__init__(**kwargs)
        self.items = items

class MainWidget(ScreenManager, HeadlessWidget):
    """Screen manager."""

    page_index: int = 0
    pages: list[PageWidget]
    current_menu: Menu

    def __init__(self: MainWidget, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize a `MainWidget`."""
        self.pages = []
        self.current_menu = MAIN_MENU
        super().__init__(**kwargs)
        self.activate_low_fps_mode()
        Clock.schedule_interval(lambda *_: self.go_to_next_page(), 5)

    def go_to_next_page(self: MainWidget) -> None:
        """Go to the next page.

        If it is already the last page, rotate to the first page.
        """
        if len(self.current_menu['items']) == 0:
            return
        self.page_index += 1
        if self.page_index >= len(self.pages):
            self.page_index = 0
        self.transition.direction = 'up'
        self.update()

    def go_to_previous_page(self: MainWidget) -> None:
        """Go to the previous page.

        If it is already the first page, rotate to the last page.
        """
        if len(self.current_menu['items']) == 0:
            return
        self.page_index -= 1
        if self.page_index < 0:
            self.page_index = len(self.pages) - 1
        self.transition.direction = 'down'
        self.update()

    def update(self: MainWidget) -> None:
        """Activate the transition from the previously active page to the current page.

        Activate high fps mode to render the animation in high fps
        """
        self.activate_high_fps_mode()
        self.current = f'Page {self.page_index}'

    def set_current_menu(self: MainWidget, menu: Menu) -> None:
        """Set the `current_menu` and create its pages."""
        self.current_menu = menu
        for page in self.pages:
            self.remove_widget(page)
        self.pages = []
        for index, page_items in enumerate(paginate(self.current_menu['items'])):
            page = PageWidget(page_items, name=f'Page {index}')
            self.pages.append(page)
            self.add_widget(page)

    def on_kv_post(self: MainWidget, _: Any) -> None:  # noqa: ANN401
        """Create all pages when the kv file is parsed."""
        self.set_current_menu(MAIN_MENU)
        self.transition.on_complete = lambda: self.activate_low_fps_mode()


class PaginationApp(App):
    """Pagination application."""

    root: MainWidget

def main() -> None:
    """Instantiate the `PaginationApp` and run it."""
    app = PaginationApp()
    app.run()

if __name__ == '__main__':
    main()
