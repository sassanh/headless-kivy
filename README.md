# Kivy Headless Renderer for Raspberry Pi

This project demonstrates the use of the Kivy framework to create a headless renderer for a Raspberry Pi. The renderer is specifically designed for and tested with the ST7789 SPI display, but it should work with other SPI displays as well. The code utilizes the Adafruit RGB Display library to communicate with the display. The renderer is optimized to not update the LCD if nothing has changed in the frame.

## Requirements

- Raspberry Pi 4
- SPI Display (tested with ST7789 module)
- numpy
- Kivy (version 2.0.0 or later)
- Adafruit RGB Display library

## Installation

To install the required libraries and dependencies, run the following command:

```sh
pip install numpy kivy adafruit-circuitpython-rgb-display
```

## Usage

1. Clone this repository and navigate to the project folder.
1. Call setup_headless() before inheriting the Headless class for the root widget of your application, and provide the optional parameters as needed. For example:

   ```python
   setup_headless(
       max_fps=20,
       width=240,
       height=240,
       baudrate=96000000,
       debug_mode=False,
       display_class=ST7789,
       double_buffering=True,
       synchronous_clock=True,
   )
   ```

1. Inherit the Headless class for the root widget of your Kivy application. For example:

   ```python
   class FboFloatLayout(FloatLayout, Headless):
       pass
   ```

1. Run the Kivy app as you normally would.

## Important Note

This project has only been tested with the ST7789 SPI display module. Other display modules might not be compatible or may require changing the parameters or even modifications to the code.

## License

This project is released under the MIT License.
