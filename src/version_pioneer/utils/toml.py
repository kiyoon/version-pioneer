from __future__ import annotations

import sys
from os import PathLike
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_toml(file: str | PathLike) -> dict[str, Any]:
    with open(file, "rb") as f:
        return tomllib.load(f)


def get_toml_value(
    toml_dict: dict[str, Any],
    keys: list[str],
    *,
    default: Any = None,
    raise_error: bool = False,
    toml_path_for_error: str = "pyproject.toml",
    return_path_object: bool = False,
) -> Any:
    """
    Args:
        return_path_object: Return a path object safely (when returning a default, don't convert to Path).
    """
    if len(keys) == 0:
        raise ValueError("keys must not be empty")

    if default is not None and raise_error:
        raise ValueError("default and raise_error cannot both be set.")

    for k in keys:
        if k not in toml_dict:
            key = ".".join(keys)
            if raise_error:
                raise KeyError(f"Missing key {key} in {toml_path_for_error}")
            return default
        toml_dict = toml_dict[k]

    value: Any = toml_dict

    if return_path_object:
        return Path(value)
    return value


def find_pyproject_toml(project_dir: str | PathLike | None = None) -> Path:
    """
    Find the pyproject.toml file in the current directory or any parent directory.
    """
    from .files import find_root_dir_with_file

    if project_dir is None:
        project_dir = Path.cwd()
    return find_root_dir_with_file(project_dir, "pyproject.toml") / "pyproject.toml"
