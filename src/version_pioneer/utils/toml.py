from __future__ import annotations

import sys
from os import PathLike
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_toml(file: str | PathLike) -> dict[str, Any]:
    with open(file, "rb") as f:
        return tomllib.load(f)
