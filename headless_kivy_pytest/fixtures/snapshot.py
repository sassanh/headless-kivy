"""Let the test check snapshots of the window during execution."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from str_to_bool import str_to_bool

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.fixtures import SubRequest
    from numpy._typing import NDArray


def write_image(image_path: Path, array: NDArray) -> None:
    """Write the `NDAarray` as an image to the given path."""
    import png

    png.Writer(
        alpha=True,
        width=array.shape[0],
        height=array.shape[1],
        greyscale=False,  # pyright: ignore [reportArgumentType]
        bitdepth=8,
    ).write(
        image_path.open('wb'),
        array.reshape(-1, array.shape[0] * 4).tolist(),
    )


class WindowSnapshot:
    """Context object for tests taking snapshots of the window."""

    def __init__(
        self: WindowSnapshot,
        *,
        test_id: str,
        path: Path,
        override: bool,
        make_screenshots: bool,
        prefix: str | None,
    ) -> None:
        """Create a new window snapshot context."""
        self.prefix = prefix
        self._is_failed = False
        self._is_closed = False
        self.override = override
        self.make_screenshots = make_screenshots
        self.test_counter: dict[str | None, int] = defaultdict(int)
        file = path.with_suffix('').name
        self.results_dir = Path(
            path.parent / 'results' / file / test_id.split('::')[-1][5:],
        )
        if self.results_dir.exists():
            prefix_element = ''
            if self.prefix:
                prefix_element = self.prefix + '-'
            for file in self.results_dir.glob(
                f'window-{prefix_element}*'
                if override
                else f'window-{prefix_element}*.mismatch.*',
            ):
                file.unlink()
        self.results_dir.mkdir(parents=True, exist_ok=True)

    @property
    def hash(self: WindowSnapshot) -> str:
        """Return the hash of the content of the window."""
        import hashlib

        from headless_kivy import HeadlessWidget

        array = HeadlessWidget.raw_data
        data = array.tobytes()
        sha256 = hashlib.sha256()
        sha256.update(data)
        return sha256.hexdigest()

    def get_filename(self: WindowSnapshot, title: str | None) -> str:
        """Get the filename for the snapshot."""
        title_element = ''
        if title:
            title_element = title + '-'
        prefix_element = ''
        if self.prefix:
            prefix_element = self.prefix + '-'
        return (
            f"""window-{prefix_element}{title_element}{self.test_counter[title]:03d}"""
        )

    def take(self: WindowSnapshot, title: str | None = None) -> None:
        """Take a snapshot of the content of the window."""
        if self._is_closed:
            msg = (
                'Snapshot context is closed, make sure `window_snapshot` is before any '
                'fixture dispatching actions in the fixtures list'
            )
            raise RuntimeError(msg)

        from pathlib import Path

        from headless_kivy import HeadlessWidget

        filename = self.get_filename(title)
        path = Path(self.results_dir / filename)
        hash_path = path.with_suffix('.hash')
        image_path = path.with_suffix('.png')
        hash_mismatch_path = path.with_suffix('.mismatch.hash')
        image_mismatch_path = path.with_suffix('.mismatch.png')

        array = HeadlessWidget.raw_data

        new_snapshot = self.hash
        if self.override:
            hash_path.write_text(f'// {filename}\n{new_snapshot}\n')
            if self.make_screenshots:
                write_image(image_path, array)
        else:
            if hash_path.exists():
                old_snapshot = hash_path.read_text().split('\n', 1)[1][:-1]
            else:
                old_snapshot = None
            if old_snapshot != new_snapshot:
                self._is_failed = True
                hash_mismatch_path.write_text(  # pragma: no cover
                    f'// MISMATCH: {filename}\n{new_snapshot}\n',
                )
                if self.make_screenshots:
                    write_image(image_mismatch_path, array)
            elif self.make_screenshots:
                write_image(image_path, array)
            assert (
                new_snapshot == old_snapshot
            ), f'Window snapshot mismatch - {filename}'

        self.test_counter[title] += 1

    def close(self: WindowSnapshot) -> None:
        """Close the snapshot context."""
        self._is_closed = True
        if self._is_failed:
            return
        for title in self.test_counter:
            filename = self.get_filename(title)
            hash_path = (self.results_dir / filename).with_suffix('.hash')

            assert not hash_path.exists(), f'Snapshot {filename} not taken'


@pytest.fixture
def snapshot_prefix() -> str | None:
    """Return the prefix for the snapshots."""
    return None


@pytest.fixture
def window_snapshot(
    request: SubRequest,
    snapshot_prefix: str | None,
) -> Generator[WindowSnapshot, None, None]:
    """Take a screenshot of the window."""
    override = (
        request.config.getoption(
            '--override-window-snapshots',
            default=cast(
                Any,
                str_to_bool(os.environ.get('UBO_TEST_OVERRIDE_SNAPSHOTS', 'false'))
                == 1,
            ),
        )
        is True
    )
    make_screenshots = (
        request.config.getoption(
            '--make-screenshots',
            default=cast(
                Any,
                str_to_bool(os.environ.get('UBO_TEST_MAKE_SCREENSHOTS', 'false')) == 1,
            ),
        )
        is True
    )

    context = WindowSnapshot(
        test_id=request.node.nodeid,
        path=request.node.path,
        override=override,
        make_screenshots=make_screenshots,
        prefix=snapshot_prefix,
    )
    yield context
    context.close()
