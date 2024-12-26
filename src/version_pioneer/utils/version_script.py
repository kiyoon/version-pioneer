from __future__ import annotations

import json
import logging
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Literal, TypeVar

from version_pioneer import template
from version_pioneer.utils.toml import (
    find_pyproject_toml,
    get_toml_value,
    load_toml,
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


def find_version_script_from_pyproject_toml_dict(
    pyproject_toml_dict: dict[str, Any],
    *,
    either_versionfile_or_versionscript: bool = True,
):
    versionscript: Path | None = get_toml_value(
        pyproject_toml_dict,
        ["tool", "version-pioneer", "versionscript"],
        return_path_object=True,
    )

    if versionscript is None:
        # NOTE: even if we end up loading versionfile-sdist, we still need to check the valid config.
        raise KeyError(
            "Missing key tool.version-pioneer.versionscript in pyproject.toml"
        )

    if either_versionfile_or_versionscript:
        versionfile: Path | None = get_toml_value(
            pyproject_toml_dict,
            ["tool", "version-pioneer", "versionfile-sdist"],
            return_path_object=True,
        )
        if versionfile is not None and versionfile.exists():
            return versionfile

    if not versionscript.exists():
        raise FileNotFoundError(f"Version script not found: {versionscript}")

    return versionscript


def find_version_script_from_project_dir(
    project_dir: str | PathLike | None = None,
    *,
    either_versionfile_or_versionscript: bool = True,
):
    """
    Args:
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

    pyproject_toml_file = find_pyproject_toml(project_dir)
    pyproject_toml = load_toml(pyproject_toml_file)

    return pyproject_toml_file.parent / find_version_script_from_pyproject_toml_dict(
        pyproject_toml,
        either_versionfile_or_versionscript=either_versionfile_or_versionscript,
    )


def exec_version_script_code(version_script_code: str) -> VersionDict:
    """
    Execute `get_version_dict()` in _version.py.
    """
    module_globals = {}
    exec(version_script_code, module_globals)
    return module_globals["get_version_dict"]()


def exec_version_script(
    version_script_path: str | PathLike,
) -> VersionDict:
    """Execute _version.py to get __version_dict__."""
    version_script_path = Path(version_script_path)
    code = version_script_path.read_text()
    return exec_version_script_code(code)


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
