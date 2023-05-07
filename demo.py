import os

from headless import Headless, setup_headless
from logger import logger

os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_NO_CONFIG"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
# os.environ['KIVY_NO_CONSOLELOG'] = '1'

import kivy  # noqa
from kivy.animation import Animation  # noqa
from kivy.app import App  # noqa
from kivy.clock import Clock  # noqa
from kivy.factory import Factory  # noqa
from kivy.uix.floatlayout import FloatLayout  # noqa

setup_headless()


class FboFloatLayout(FloatLayout, Headless):
    pass


class ScreenLayerApp(App):
    def animate(self, *_):
        self.button.x = 0
        logger.debug("Animation started")
        Animation(x=self.float_layout.width - self.button.width, duration=3).start(
            self.button
        )

    def build(self):
        self.float_layout = FboFloatLayout()

        self.button = Factory.Button(size_hint=(None, None))
        self.float_layout.add_widget(self.button)

        def anim_btn(*_):
            if self.button.pos[0] == 0:
                Animation(
                    x=self.float_layout.width - self.button.width, duration=3
                ).start(self.button)
            else:
                Animation(x=0, duration=3).start(self.button)

        self.button.bind(on_press=anim_btn)

        self.animate()
        Clock.schedule_interval(self.animate, 6)

        return self.float_layout


if __name__ == "__main__":
    app = ScreenLayerApp()
    app.run()
