# Changelog

## Upcoming

- feat: divide each frame into multiple rectangles, compare rectangle with the same rectangle in the previous frame and update only the changed ones

## Version 0.11.1

- fix: change type of `kwargs` in `HeadlessWidget.__init__` to `object`

## Version 0.11.0

- refactor: drop all the fps handling and render scheduling logic in favor of `Canvas`'s `Callback` instruction which gets called only when new drawing is done

## Version 0.10.1

- chore: set dependencies for `[test]` extra

## Version 0.10.0

- chore: migrate from poetry to uv for the sake of improving performance and dealing with conflicting sub-dependencies
- refactor: make it ready to be used for local widgets

## Version 0.9.8

- fix: an error in data slicing causing failure when HDMI display is connected

## Version 0.9.7

- fix: slice the data in case it exceeds the size of the display

## Version 0.9.6

- fix: make it compatible with kivy 3

## Version 0.9.5

- refactor: set minimum version of `kivy` to `2.1.0` (used to be `2.3.0`)

## Version 0.9.4

- refactor: update snapshot fixture with latest changes

## Version 0.9.3

- refactor: migrate from `uint16` to `uint8` as each channel of the RGB image is
  a single byte
- feat: add alpha channel ... yet again
- feat: add a demo app based on the code provided [here](https://github.com/sassanh/headless-kivy/issues/13#issuecomment-2211547084)
- fix: the order of width and height in different places so that it works when the
  screen is not a square - closes #12, closes #13

## Version 0.9.2

- fix: apply rotations and flips and drop alpha channel on data before storing it
  in `raw_data`

## Version 0.9.1

- fix: consider alpha channel in the data stored in `raw_data` field of `HeadlessWidget`

## Version 0.9.0

- refactor: remove all features specific to Raspberry Pi, now it is a general headless
  Kivy library suitable for different platforms and test environments
- build: rename project to `headless-kivy` as it is not specific to Raspberry Pi
  anymore
- build: update repository to <https://github.com/sassanh/headless-kivy>

## Version 0.8.2

- refactor: drop code for positioning the window on the screen

## Version 0.8.1

- refactor: drop `is_test_environment`, the code using headless kivy should be
  responsible for setting up the environment so that it can fully customize the
  configuration

## Version 0.8.0

- refactor: use `str_to_bool` of `python-strtobool` instead of `strtobool` of `distutils`
- feat: add snapshot fixture

## Version 0.7.4

- feat: add `rotation`, `flip_horizontal`, and `flip_vertical` parameters to
  `SetupHeadlessConfig` to allow configuration of the display orientation

## Version 0.7.3

- feat: configurable rotation and flip parameters
- feat: let the user render a splash screen before the first frame is ready to be
  rendered, if not provided, it renders a black screen

## Version 0.7.2

- fix: revert numpy data structure storing display data to uint16 as 2 bytes are
  used per pixel

## Version 0.7.1

- fix: don't interact with window system when running headless for tests

## Version 0.7.0

- feat: render relevant parts of the screen only
- feat: keep a copy of the raw data transferred to the display in `config._display.raw_data`

## Version 0.6.1

- chore: GitHub workflow to publish pushes on `main` branch to PyPI
- chore: create GitHub release for main branch in GitHub workflows

## Version 0.6.0

- refactor: `HeadlessWidget` is not a singleton anymore, config migrated to config
  module
- refactor: initializing display and config is now done in `setup_headless_kivy`
- feat: class method `get_instance` to get the closest parent instance of type `HeadlessWidget`

## Version 0.5.12

- fix: make sure `kivy.core.window` is loaded in `setup_headless` to avoid
  segmentation fault

## Version 0.5.11

- docs: remove instructions to deal with legacy Raspbian from `README.md`

## Version 0.5.10

- feat: ensure `setup_headless` is called before instantiating `HeadlessWidget`
- feat: periodically write snapshots of the screen to filesystem in debug mode for
  remote debugging
- refactor: fix pyright and ruff errors and warnings by faking modules
- refactor: split `__init__.py` into several files

## Version 0.5.9

- refactor: make `synchronous_clock` enabled by default

## Version 0.5.8

- refactor: avoid unnecessary scheduled calls of `render_on_display`
- refactor: make `automatic_fps` enabled by default

## Version 0.5.7

- feat: cancel clock event when kivy app stops

## Version 0.5.6

- fix: ignore data hash and render a single frame after resume

## Version 0.5.3

- feat: add `clear_at_exit` setting and `pause` and `resume` methods

## Version 0.5.2

- chore: simplify `pyproject.toml` and the setup instructions

## Version 0.5.1

- fix: incorrect local import path

## Version 0.5.0

- chore: drop support for python 3.9 and 3.10

## Version 0.4.2

- chore: migrate from poetry groups to poetry extras

## Version 0.4.1

- chore: update development installation command in `README.md`

## Version 0.4.0

- chore: add dev extra, remove watchdog and cython

## Version 0.3.7

- chore: update typing-extensions

## Version 0.3.6

- chore: migrate repository to <https://github.com/ubopod/headless-kivy-pi>

## Version 0.3.5

- chore: add CHANGELOG.md

## Version 0.3.4

- feat: add stencil support in HeadlessWidget's framebuffer

## Version 0.3.3

- chore: update packages
- docs: add icons in README.md
- chore: drop unused dependencies

## Version 0.3.0

- refactor: make some methods of HeadlessWidget class methods
- docs: update the README.md file
- chore: add license file
- chore: update lockfile

## Version 0.2.2

- chore: github action for building wheels

## Version 0.2.1

- fix: make adafruit-circuitpython-rgb-display conditionally install only on raspberry
  pi

## Version 0.2.0

- chore: remove demo files
- feat: keyboard navigation for pagination demo
- feat: add typings and docs
- docs: add pagination demo
- chore: update poetry packages and config
- feat: add activate_low_fps_mode and activate_high_fps_mode to manually set fps
  when needed
- feat: add logging and improve fps handler
- docs: add sdl installation instructions and a reference to demo.py in README.md
- feat: drop Kivy FPS to min_fps when the user interface is idle
- feat: Add default values for `setup_headless()` based on environment variables
- docs: add demo.py to show all the features in action
- docs: add README.md
- feat: avoid sending data to the lcd when the current frame is the same as the last
  one
- feat: add double buffering
- feat: add synchronous mode to save CPU time by avoiding Kivy from rendering frames
  when last frame is not yet rendered on the lcd

## Version 0.1.0

- feat: implement Headless widget to render content on SPI display without needing
  a display server/window manager
