# Kivy Headless Renderer

This project provides utilities to render Kivy applications headlessly. It can be
used in test environments, it also provides tools for snapshot testing.
It can also be used on a Raspberry Pi or similar devices to render the Kivy application
on a custom display like an SPI display.

The renderer is optimized to not schedule a render when nothing has changed since
the last rendered frame.

## 📦 Installation

```sh
pip install headless-kivy
```

To use its test tools, you can install it with the following command:

```sh
pip install headless-kivy[dev]
```

## 🛠 Usage

1. Call setup_headless() before inheriting the `HeadlessWidget` class for the root
   widget of your application, and provide the optional parameters as needed. For
   example (these are all default values, you only need to provide the ones you want
   to change):

   ```python
   setup_headless(
       width=240,
       height=240,
       is_debug_mode=False,
       display_class=ST7789,
       double_buffering=True,
   )
   ```

1. Inherit the `HeadlessWidget` class for the root widget of your Kivy application.
   For example:

   ```python
   class FboFloatLayout(FloatLayout, HeadlessWidget):
       pass
   ```

1. Run the Kivy app as you normally would.

Checkout [Ubo App](https://github.com/ubopod/ubo-app) to see a sample implementation.

### ⚙️ Parameters

These parameters can be set to control the behavior of headless kivy:

#### `callback`

A callback function that will be called when the screen data changes. It should
have this signature:

```python
def render(
    *,
    rectangle: tuple[int, int, int, int],
    data: NDArray[np.uint8],
    data_hash: int,
    last_render_thread: Thread,
) -> None: ...
```

`rectangle` is a tuple with the coordinates and size of the changed area in the
`(x, y, width, height)` format.

`data` is a numpy array with the screen RGB data in the `uint8` format. So its
dimensions are `(width, height, 3)`.

`data_hash` is probably not very useful for most cases, it is mostly for logging
and debugging purposes.

It always runs in a new thread, the previous thread is provided so that it can call
its `join` if desired.

#### `width`

The width of the display in pixels.

#### `height`

The height of the display in pixels.

#### `is_debug_mode`

If set to True, the application will print debug information, including FPS.

#### `double_buffering`

Is set to `True`, it will let Kivy generate the next frame while sending the last
frame to the display.

#### `rotation`

The rotation of the display. It will be multiplied by 90 degrees.

#### `flip_horizontal`

If set to `True`, it will flip the display horizontally.

#### `flip_vertical`

If set to `True`, it will flip the display vertically.

## 🤝 Contributing

You need to have [uv](https://github.com/astral-sh/uv) installed on your machine.

To install the required dependencies, run the following command in the root directory of the project:

```sh
uv sync
```

## ⚠️ Important Note

This project has only been tested with the ST7789 SPI display module. Other display
modules might not be compatible or may require changing the parameters or even modifications
to the code.

## 🔒 License

This project is released under the Apache-2.0 License. See the [LICENSE](./LICENSE)
file for more details.
