# Kivy Headless Renderer for Raspberry Pi

This project demonstrates the use of the Kivy framework to create a headless renderer for a Raspberry Pi. The renderer is specifically designed for and tested with the ST7789 SPI display, but it should work with other SPI displays as well. The code utilizes the Adafruit RGB Display library to communicate with the display. The renderer is optimized to not update the LCD if nothing has changed in the frame.

## ⚡️ Requirements

- Raspberry Pi 4 or 5
- SPI Display (tested with ST7789 module)

## 📦 Installation

You can install it using this handle: headless-kivy-pi@git+<https://github.com/ubopod/headless-kivy-pi.git>

```sh
pip install headless-kivy-pi
```

To work on a non-RPi environment, run this:

```sh
# pip:
pip install headless-kivy-pi[dev]
# poetry:
poetry --group dev headless-kivy-pi
```

## 🚀 Usage

1. Call setup_headless() before inheriting the `HeadlessWidget` class for the root widget of your application, and provide the optional parameters as needed. For example (these are all default values, you only need to provide the ones you want to change):

   ```python
   setup_headless(
       min_fps=1,
       max_fps=30,
       width=240,
       height=240,
       baudrate=60000000,
       debug_mode=False,
       display_class=ST7789,
       double_buffering=True,
       synchronous_clock=True,
       automatic_fps=True,
       clear_at_exit=True,
   )
   ```

1. Inherit the `HeadlessWidget` class for the root widget of your Kivy application. For example:

   ```python
   class FboFloatLayout(FloatLayout, HeadlessWidget):
       pass
   ```

1. Run the Kivy app as you normally would.

Checkout [Ubo App](https://github.com/ubopod/ubo-app) to see a sample implementation.

### ⚙️ Parameters

These parameters can be set to control the behavior of headless kivy pi:

#### `min_fps`

Minimum frames per second for when the Kivy application is idle.

#### `max_fps`

Maximum frames per second for the Kivy application.

#### `width`

The width of the display in pixels.

#### `height`

The height of the display in pixels.

#### `baudrate`

The baud rate for the display connection.

#### `debug_mode`

If set to True, the application will print debug information, including FPS.

#### `display_class`

The display class to use (default is ST7789).

#### `double_buffering`

Is set to `True`, it will let Kivy generate the next frame while sending the last frame to the display.

#### `synchronous_clock`

If set to `True`, Kivy will wait for the LCD before rendering next frames. This will cause Headless to skip frames if they are rendered before the LCD has finished displaying the previous frames. If set to False, frames will be rendered asynchronously, letting Kivy render frames regardless of display being able to catch up or not at the expense of possible frame skipping.

#### `automatic_fps`

If set to `True`, it will monitor the hash of the screen data, if this hash changes, it will increase the fps to the maximum and if the hash doesn't change for a while, it will drop the fps to the minimum.

#### `clear_at_exit`

If set to `True`, it will clear the screen before exiting.

## ⚒️ Contribution

You need to have [Poetry](https://python-poetry.org/) installed on your machine.

To install poetry in Raspbian you need to follow these instructions to install rust compiler, this is temporary until [this issue](https://github.com/python-poetry/poetry/issues/7645) is resolved:

```sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt-get install pkg-config libssl-dev
curl -sSL https://install.python-poetry.org | python3 -
```

After having poetry, to install the required dependencies, run the following command:

```sh
poetry install
```

Also be aware of [this issue](https://github.com/python-poetry/poetry/issues/1917) and until it is resolved you can manually disable keyring by prefixing your poetry commands like this:

```sh
PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring poetry install
```

## ⚠️ Important Note

This project has only been tested with the ST7789 SPI display module. Other display modules might not be compatible or may require changing the parameters or even modifications to the code.

## 📜 License

This project is released under the Apache-2.0 License.
