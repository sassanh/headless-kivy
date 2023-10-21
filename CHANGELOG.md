# Changelog

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

- fix: make adafruit-circuitpython-rgb-display conditionally install only on raspberry pi

## Version 0.2.0

- chore: remove demo files
- feat: keyboard navigation for pagination demo
- feat: add typings and docs
- docs: add pagination demo
- chore: update poetry packages and config
- feat: add activate_low_fps_mode and activate_high_fps_mode to manually set fps when needed
- feat: add logging and improve fps handler
- docs: add sdl installation instructions and a reference to demo.py in README.md
- feat: drop Kivy FPS to min_fps when the user interface is idle
- feat: Add default values for `setup_headless()` based on environment variables
- docs: add demo.py to show all the features in action
- docs: add README.md
- feat: avoid sending data to the lcd when the current frame is the same as the last one
- feat: add double buffering
- feat: add synchronous mode to save CPU time by avoiding Kivy from rendering frames when last frame is not yet rendered on the lcd

## Version 0.1.0

- feat: implement Headless widget to render content on SPI display without needing a display server/window manager
