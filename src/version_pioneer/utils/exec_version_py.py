from __future__ import annotations

import json
import logging
import textwrap
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Literal, TypeVar

from version_pioneer import VersionDict, template
from version_pioneer.utils.toml import (
    find_pyproject_toml,
    get_toml_value,
    load_toml,
)

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


def find_version_py_from_project_dir(
    project_dir: str | PathLike | None = None,
):
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    if project_dir.is_file():
        raise NotADirectoryError(f"{project_dir} is not a directory.")

    pyproject_toml_file = find_pyproject_toml(project_dir)
    pyproject_toml = load_toml(pyproject_toml_file)
    version_py_file = Path(
        get_toml_value(
            pyproject_toml, ["tool", "version-pioneer", "versionfile-source"]
        )
    )
    if not version_py_file.exists():
        version_py_file2 = Path(
            get_toml_value(
                pyproject_toml, ["tool", "version-pioneer", "versionfile-build"]
            )
        )
        if not version_py_file2.exists():
            raise FileNotFoundError(
                f"Version file not found: {version_py_file} or {version_py_file2}"
            )
        return version_py_file2
    return version_py_file


def exec_version_py_code_to_get_version_dict(
    version_py_code: str, cwd: str | PathLike | None = None
) -> VersionDict:
    """
    Execute _version.py code to get __version_dict__.

    Args:
        cwd: If set, remove line starting with `__version_dict__` and `__version__`
            and add `__version_dict__ = get_version_dict(cwd="{cwd}")` at EOF.
            This is useful during some build systems where it is executed in a temporary directory.

    Raises:
        NameError: name 'get_version_dict' is not defined
            This means the _version.py file is already resolved to a constant version, thus changing cwd is not allowed.
            This only happens when `cwd` is set.
    """
    if cwd is not None:
        version_py_code_list = version_py_code.splitlines()
        original_line_count = len(version_py_code_list)

        # remove __version__ lines
        version_py_code_list = [
            line
            for line in version_py_code_list
            if not line.startswith("__version__")
            and not line.startswith("__version_dict__")
        ]

        # two lines should have been removed
        if len(version_py_code_list) == original_line_count - 2:
            version_py_code_list.append(
                f'__version_dict__ = get_version_dict(cwd="{cwd}")'
                # f"__version_dict__ = {{'version': '0.3.0', 'full': '{cwd}', 'dirty': False}}"
            )
            version_py_code = "\n".join(version_py_code_list)
        else:
            logger.warning(
                textwrap.dedent(
                    """No lines removed or more than 2 lines removed. This means users have modified the code.
                    Rather than failing, we will just add the line at the end.
                    This may evaluate version twice but it's not a big deal."""
                )
            )
            version_py_code += f'\n__version_dict__ = get_version_dict(cwd="{cwd}")'

    module_globals = {}
    exec(version_py_code, module_globals)
    return module_globals["__version_dict__"]


def exec_version_py_to_get_version_dict(version_py_path: str | PathLike) -> VersionDict:
    """Execute _version.py to get __version_dict__."""
    version_py_path = Path(version_py_path)
    code = version_py_path.read_text()
    return exec_version_py_code_to_get_version_dict(code)


def exec_version_py_to_get_version(version_py_path: str | PathLike) -> str:
    """Execute _version.py to get __version__."""
    return exec_version_py_to_get_version_dict(version_py_path)["version"]


def version_dict_to_str(
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
