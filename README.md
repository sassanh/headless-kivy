# Headless Kivy

Provides utilities to render Kivy applications headlessly. It calls a callback whenever something has changed in the framebuffer in a locality.

It can be used to render the Kivy application on a custom display like an SPI display, it provides tools for local updates, limiting the bandwidth and limiting the fps based on the spec of the display.

It can also be used in test environments with it tools for snapshot testing.

You can control the orientation of the display and flipping the display horizontally and vertically.

The renderer is optimized to not schedule a render when nothing has changed since the last rendered frame, by default it divides the screen into tiles and checks each tile for changes separately.

It can be configured to use double buffering, so that the next frame is generated while the last frame is being transmitted to the display.

You can have multiple instances of the headless renderer in the same application, each works as a portal to your display (or multiple different displays).

## 📦 Installation

```sh
pip install headless-kivy
```

To use its test tools, you can install it with the following command:

```sh
pip install headless-kivy[test]
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
       bandwidth_limit=1000000, # number of pixels per second
       bandwidth_limit_window=.1, # allow bandwidth_limit x bandwidth_limit_window pixels to be transmitted in bandwidth_limit_window seconds
       bandwidth_limit_overhead=1000, # each draw command, regardless of the size, has equivalent of this many pixels of cost in bandwidth
       is_debug_mode=False,
       rotation=1, # gets multiplied by 90 degrees
       flip_horizontal=True,
       double_buffering=True, # let headless kivy generate the next frame while the previous callback is still running
       window_mode='hidden', # 'hidden' (default) renders off-screen; 'auto' lets SDL grab a physical display
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

#### `bandwidth_limit`

Maximum bandwidth usage in pixels per second, no limit if set to 0.

#### `bandwidth_limit_window`

Length of the time window in seconds to check the bandwidth limit.

#### `bandwidth_limit_overhead`

The overhead of each draw command in pixels, regardless of its size.

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

#### `window_mode`

Controls whether Kivy is allowed to grab a physical display. Two values:

- `'hidden'` (default): headless-kivy sets `SDL_VIDEODRIVER=offscreen` before Kivy initializes, so SDL renders to an off-screen OpenGL context. No HDMI / DSI / KMSDRM connector is touched, and the FBO callback still receives frames. This is the right setting when the only "real" display you care about is driven from the callback (e.g. an SPI panel on a Raspberry Pi) — an attached HDMI monitor will keep showing whatever it was showing before (typically the Linux console) instead of being hijacked by Kivy's window.
- `'auto'`: headless-kivy does not touch `SDL_VIDEODRIVER`; SDL picks a display normally. On a Pi kiosk this means the KMSDRM video driver will grab the framebuffer and Kivy's window will cover the connected display.

You can also set this via environment variable:

```bash
export HEADLESS_KIVY_WINDOW_MODE=auto
```

If `SDL_VIDEODRIVER` is already set in the environment when you call `setup_headless_kivy`, headless-kivy will respect it and leave it alone (an INFO log line is emitted in that case).

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
