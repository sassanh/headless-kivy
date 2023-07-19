from __future__ import annotations
import os
from typing_extensions import List, NotRequired, TypedDict

from src.headless.headless import HeadlessWidget, setup_headless

os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_NO_CONFIG"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
# os.environ['KIVY_NO_CONSOLELOG'] = '1'

setup_headless()

from kivy.app import App, Widget  # noqa
from kivy.clock import Clock  # noqa
from kivy.core.window import (ColorProperty, ListProperty,  # noqa
                              StringProperty)
from kivy.graphics import Color  # noqa
from kivy.uix.screenmanager import Screen, ScreenManager  # noqa


class Item(TypedDict):
    label: str
    color: NotRequired[List[float]]
    sub_items: NotRequired[List['Item']]


PAGE_SIZE = 3
ITEMS: List[Item] = [
    {
        "label": "First Item",
        "sub_items": [
            {
                "label":"Back",
                "color": [],
            },
        ],
    },
    {
        "label": "Second Item",
        "color": [1,0,1,1],
    },
    {
        "label": "Third Item",
    },
    {
        "label": "Fourth Item",
    },
]

def paginate(list):
    """Yield successive PAGE_SIZE-sized chunks from list."""
    for i in range(0, len(list), PAGE_SIZE):
        yield list[i:i + PAGE_SIZE]

class ItemWidget(Widget):
    color = ColorProperty((1, 1, 1, 1))
    label = StringProperty()

class PageWidget(Screen):
    items = ListProperty([])

    def __init__(self, items: List[Item], **kwargs):
        super(PageWidget, self).__init__(**kwargs)
        self.items = items

class Main(ScreenManager, HeadlessWidget):
    page_index: int = 0
    pages: list[PageWidget] = []

    def __init__(self, **kwargs):
        super(Main, self).__init__(**kwargs)
        self.activate_low_fps_mode()
        Clock.schedule_interval(lambda *_: self.go_to_next_page(), 5)

    def go_to_next_page(self):
        if len(ITEMS) == 0:
            return
        self.page_index += 1
        if self.page_index >= len(self.pages):
            self.page_index = 0
        self.transition.direction = 'up'
        self.update()

    def go_to_previous_page(self):
        if len(ITEMS) == 0:
            return
        self.page_index -= 1
        if self.page_index < 0:
            self.page_index = len(self.pages) - 1
        self.transition.direction = 'down'
        self.update()

    def update(self):
        print(f'Switching to page {self.page_index}')
        self.activate_high_fps_mode()
        self.current = f'Page {self.page_index}'

    def on_kv_post(self, _):
        for index, page in enumerate(paginate(ITEMS)):
            page = PageWidget(page, name = f'Page {index}')
            self.pages.append(page)
            self.add_widget(page)
        self.transition.on_complete = lambda: self.activate_low_fps_mode()

class PaginationApp(App):
    root: Main


def main():
    app = PaginationApp()
    app.run()

if __name__ == '__main__':
    main()
