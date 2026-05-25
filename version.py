# ruff: noqa: D100, D103
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import hatch_vcs.version_source


def get_version() -> str:
    if os.environ.get('PRETEND_VERSION'):
        return os.environ['PRETEND_VERSION']
    version_source = hatch_vcs.version_source.VCSVersionSource(Path(), {})
    vcs_version = version_source.get_version_data()['version']

    date_string = datetime.now(UTC).strftime('%y%m%d')

    def make_suffix(m: re.Match[str]) -> str:
        hash_part = m.group(1)
        ordinals = ''.join(str(ord(c)) for c in hash_part)
        # Keep the dev suffix within 18 digits so it stays under 64-bit int limit.
        return '.dev' + (date_string + ordinals)[:18]

    return re.sub(
        r'\.dev\d+\+([^.]+)(?:\.d.*)?$',
        make_suffix,
        vcs_version,
    )
