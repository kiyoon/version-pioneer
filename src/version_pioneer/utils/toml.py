from __future__ import annotations

import sys
from collections.abc import Iterable
from os import PathLike
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class InvalidConfigError(Exception):
    pass


def load_toml(file: str | PathLike) -> dict[str, Any]:
    with open(file, "rb") as f:
        return tomllib.load(f)


def get_toml_value(
    toml_dict: dict[str, Any],
    keys: list[str],
    *,
    toml_path_for_error: str = "pyproject.toml",
) -> Any:
    value = toml_dict
    for k in keys:
        if k not in value:
            key = ".".join(keys)
            raise InvalidConfigError(f"Missing key {key} in {toml_path_for_error}")
        value = value[k]
    return value


def find_root_dir_with_file(
    source: str | PathLike, marker: str | Iterable[str]
) -> Path:
    """
    Find the first parent directory containing a specific "marker", relative to a file path.
    """
    source = Path(source).resolve()
    if isinstance(marker, str):
        marker = {marker}

    while source != source.parent:
        if any((source / m).exists() for m in marker):
            return source

        source = source.parent

    raise FileNotFoundError(f"File {marker} not found in any parent directory")


def find_pyproject_toml(project_dir: str | PathLike | None = None) -> Path:
    """
    Find the pyproject.toml file in the current directory or any parent directory.
    """
    if project_dir is None:
        project_dir = Path.cwd()
    return find_root_dir_with_file(project_dir, "pyproject.toml") / "pyproject.toml"
