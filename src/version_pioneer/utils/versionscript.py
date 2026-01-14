from __future__ import annotations

import json
import logging
import tokenize
from enum import Enum
from os import PathLike
from pathlib import Path
from types import CodeType
from typing import Any, Literal, TypeVar

from version_pioneer import template
from version_pioneer.utils.config import (
    get_config_value,
    load_config,
    normalize_pyproject_dict_to_config,
)
from version_pioneer.versionscript import VersionDict

logger = logging.getLogger(__name__)


class ResolutionFormat(str, Enum):
    python = "python"
    json = "json"
    version_string = "version-string"


RESOLUTION_FORMAT_TYPE = TypeVar(
    "RESOLUTION_FORMAT_TYPE",
    Literal["python", "json", "version-string"],
    ResolutionFormat,
)


def find_versionscript_from_config(
    config: dict[str, Any],
    *,
    either_versionfile_or_versionscript: bool = True,
    config_source: str = "config",
) -> Path:
    """
    Find versionscript from a normalized config dict.

    Args:
        config: Normalized config dict (without tool.version-pioneer prefix)
        either_versionfile_or_versionscript: If True, return versionfile-sdist if it exists
        config_source: Description for error messages
    """
    versionscript: Path | None = get_config_value(
        config,
        "versionscript",
        return_path_object=True,
    )

    if versionscript is None:
        # NOTE: even if we end up loading versionfile-sdist, we still need to check the valid config.
        # Include full key path in error for pyproject.toml
        if "pyproject.toml" in config_source:
            key_prefix = "tool.version-pioneer."
        else:
            key_prefix = ""
        raise KeyError(f"Missing key {key_prefix}versionscript in {config_source}")

    if either_versionfile_or_versionscript:
        versionfile: Path | None = get_config_value(
            config,
            "versionfile-sdist",
            return_path_object=True,
        )
        if versionfile is not None and versionfile.exists():
            return versionfile

    if not versionscript.exists():
        raise FileNotFoundError(f"Version script not found: {versionscript}")

    return versionscript


def find_versionscript_from_pyproject_toml_dict(
    pyproject_toml_dict: dict[str, Any],
    *,
    either_versionfile_or_versionscript: bool = True,
):
    """
    Find versionscript from pyproject.toml dict.

    This function is kept for backward compatibility with build hooks
    that receive pyproject.toml data directly (e.g., PDM context.config.data).
    """
    config = normalize_pyproject_dict_to_config(pyproject_toml_dict)
    return find_versionscript_from_config(
        config,
        either_versionfile_or_versionscript=either_versionfile_or_versionscript,
        config_source="pyproject.toml",
    )


def find_versionscript_from_project_dir(
    project_dir: str | PathLike | None = None,
    *,
    either_versionfile_or_versionscript: bool = True,
):
    """
    Find versionscript from project directory.

    Now supports both version-pioneer.toml and pyproject.toml.

    Args:
        project_dir: The root or child directory of the project.
        either_versionfile_or_versionscript: If True, return either versionfile-sdist if it exists,
            else versionscript.
            This is important because in sdist build, the versionfile is already evaluated
            and git tags are not available.
    """
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    if project_dir.is_file():
        raise NotADirectoryError(f"{project_dir} is not a directory.")

    config_result = load_config(project_dir)

    return config_result.project_root / find_versionscript_from_config(
        config_result.config,
        either_versionfile_or_versionscript=either_versionfile_or_versionscript,
        config_source=config_result.source,
    )


def exec_versionscript_code(versionscript_code: str | CodeType) -> VersionDict:
    """
    Execute `get_version_dict()` in _version.py.
    """
    module_globals = {}
    exec(versionscript_code, module_globals)
    return module_globals["get_version_dict"]()


def exec_versionscript(
    versionscript_path: str | PathLike,
) -> VersionDict:
    """Execute _version.py to get __version_dict__."""
    versionscript_path = Path(versionscript_path)

    # Reads using Python-source with correct encoding (PEP 263)
    # instead of assuming it's UTF-8. It replaces the following:
    # code = versionscript_path.read_text(encoding="utf-8")
    with tokenize.open(versionscript_path) as f:
        source = f.read()
    code = compile(source, str(versionscript_path), "exec", dont_inherit=True)

    return exec_versionscript_code(code)


def convert_version_dict(
    version_dict: VersionDict,
    output_format: RESOLUTION_FORMAT_TYPE,
) -> str:
    from version_pioneer import __version__

    if output_format == ResolutionFormat.python:
        return template.EXEC_OUTPUT_PYTHON.format(
            version_pioneer_version=__version__,
            version_dict=version_dict,
        )
    elif output_format == ResolutionFormat.json:
        return json.dumps(version_dict)
    elif output_format == ResolutionFormat.version_string:
        return version_dict["version"]
    else:
        raise ValueError(f"Invalid output format: {output_format}")
