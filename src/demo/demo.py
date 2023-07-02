import os

from src.headless.headless import HeadlessWidget, setup_headless
from src.headless.logger import logger

os.environ["KIVY_METRICS_DENSITY"] = "1"
os.environ["KIVY_NO_CONFIG"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
# os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.animation import Animation  # noqa
from kivy.app import App  # noqa
from kivy.clock import Clock  # noqa
from kivy.factory import Factory  # noqa
from kivy.uix.floatlayout import FloatLayout  # noqa

setup_headless()


class FboFloatLayout(FloatLayout, HeadlessWidget):
    pass


class ScreenLayerApp(App):
    def animate(self, *_):
        self.button.x = 0
        logger.debug("Animation started")
        self.float_layout.activate_high_fps_mode()
        animation = Animation(x=self.float_layout.width-self.button.width, duration=3)
        animation.start(self.button)
        animation.bind(
            on_complete=lambda *_: self.float_layout.activate_low_fps_mode(),
        )

    def build(self):
        self.float_layout = FboFloatLayout()

        self.button = Factory.Button(size_hint=(None, None))
        self.float_layout.add_widget(self.button)

        self.button.bind(on_press=self.animate)

        self.animate()
        Clock.schedule_interval(self.animate, 6)

        return self.float_layout


def main():
    app = ScreenLayerApp()
    app.run()
