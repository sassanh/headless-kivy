import time
from pathlib import Path
from typing import Type

import numpy
from adafruit_rgb_display.rgb import DisplaySPI
from kivy.app import ObjectProperty, Widget
from kivy.base import Clock
from kivy.config import Config
from kivy.graphics import Canvas, ClearBuffers, ClearColor, Color, Fbo, Rectangle

# Check if the code is running on a Raspberry Pi
IS_RPI = Path("/etc/rpi-issue").exists()
ST7789: Type[DisplaySPI]
if IS_RPI:
    import board
    import digitalio
    from adafruit_rgb_display.st7789 import ST7789
else:
    ST7789 = type("ST7789", (DisplaySPI,), {})

# Constants for calculations
BYTES_PER_PIXEL = 2
BITS_PER_BYTE = 11


# Configure the headless mode for the Kivy application and initialize the display
def setup_headless(
    max_fps: int = 20,
    width: int = 240,
    height: int = 240,
    baudrate: int = 96000000,
    debug_mode: bool = False,
    display_class: Type[DisplaySPI] = ST7789,
):
    """
    Configures the headless mode for the Kivy application.

    :param max_fps: Maximum frames per second for the Kivy application.
    :param width: The width of the display in pixels.
    :param height: The height of the display in pixels.
    :param baudrate: The baud rate for the display connection.
    :param debug_mode: If set to True, the application will print debug information, \
including FPS.
    :param display_class: The display class to use (default is ST7789).
    """
    Headless.width = width
    Headless.height = height
    Headless.debug_mode = debug_mode

    desired_fps = baudrate / (width * height * BYTES_PER_PIXEL * BITS_PER_BYTE)
    Config.set("kivy", "kivy_clock", "default")
    Config.set("graphics", "fbo", "force-hardware")
    Config.set("graphics", "fullscreen", "0")
    Config.set("graphics", "maxfps", f"{max_fps}")
    Config.set("graphics", "multisamples", "1")
    Config.set("graphics", "resizable", "0")
    Config.set("graphics", "vsync", "0")
    Config.set("graphics", "width", f"{width}")
    Config.set("graphics", "height", f"{height}")

    if debug_mode:
        print(f"Desired FPS: {desired_fps:.1f}")
        print(f'Kivy "maxfps": {max_fps}')

    if IS_RPI:
        Config.set("graphics", "window_state", "hidden")
        spi = board.SPI()
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)
        global display
        display = display_class(
            spi,
            height=height,
            width=width,
            y_offset=80,
            x_offset=0,
            rotation=180,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=baudrate,
        )


# Headless Kivy widget class rendering on SPI display
class Headless(Widget):
    texture = ObjectProperty(None, allownone=True)

    debug_mode: bool
    width: int
    height: int

    def __init__(self, **kwargs):
        if Headless.width is None or Headless.height is None:
            print('"setup_headless" should be called before instantiating "Headless"')
        super(Headless, self).__init__(**kwargs)
        self.last_second = int(time.time())
        self.rendered_frames = 0
        self.skipped_frames = 0
        self.last_hash = 0

        self.canvas = Canvas()
        with self.canvas:
            self.fbo = Fbo(size=self.size)
            self.fbo_color = Color(1, 1, 1, 1)
            self.fbo_rect = Rectangle()

        with self.fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()

        self.texture = self.fbo.texture

        self.render_on_display_event = Clock.create_trigger(
            self.render_on_display, 0, True
        )
        self.render_on_display_event()

    def add_widget(self, *args, **kwargs):
        canvas = self.canvas
        self.canvas = self.fbo
        ret = super(Headless, self).add_widget(*args, **kwargs)
        self.canvas = canvas
        return ret

    def remove_widget(self, *args, **kwargs):
        canvas = self.canvas
        self.canvas = self.fbo
        super(Headless, self).remove_widget(*args, **kwargs)
        self.canvas = canvas

    def on_size(self, _, value):
        self.fbo.size = value
        self.texture = self.fbo.texture
        self.fbo_rect.size = value

    def on_pos(self, _, value):
        self.fbo_rect.pos = value

    def on_texture(self, _, value):
        self.fbo_rect.texture = value

    def on_alpha(self, _, value):
        self.fbo_color.rgba = (1, 1, 1, value)

    def render_on_display(self, *_):
        # Only render when running on a Raspberry Pi
        if IS_RPI:
            # Increment rendered_frames/skipped_frames count every frame and reset their
            # values to zero every second.
            current_second = int(time.time())
            if current_second != self.last_second:
                if Headless.debug_mode:
                    # Print the number of skipped and rendered frames in the last second
                    print(
                        f"""Frames in {self.last_second}:
      [Skipped: {self.skipped_frames}] [Rendered: {self.rendered_frames}]"""
                    )
                self.last_second = current_second
                self.rendered_frames = 0
                self.skipped_frames = 0

            self.rendered_frames += 1

            data = numpy.frombuffer(self.texture.pixels, dtype=numpy.uint8).reshape(
                Headless.width, Headless.height, -1
            )
            data = data[:, :, :3].astype(numpy.uint16)

            color = (
                ((data[:, :, 0] & 0xF8) << 8)
                | ((data[:, :, 1] & 0xFC) << 3)
                | (data[:, :, 2] >> 3)
            )
            data = bytes(
                numpy.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()
            )
            display._block(0, 0, Headless.width - 1, Headless.height - 1, data)
