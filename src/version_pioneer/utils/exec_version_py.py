from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # NOTE: importing from version_pioneer._version is dangerous because it gets replaced to a constant during build.
    # So, we import from version_pioneer._version only in TYPE_CHECKING mode.
    from version_pioneer._version import VersionDict

from version_pioneer.utils.toml import (
    find_pyproject_toml,
    get_toml_value,
    load_toml,
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


def exec_version_py_to_get_version_dict(version_py_path: str | PathLike) -> VersionDict:
    """Execute _version.py to get __version_dict__."""
    version_py_path = Path(version_py_path)
    code = version_py_path.read_text()
    module_globals = {}
    exec(code, module_globals)
    return module_globals["__version_dict__"]


def exec_version_py_to_get_version(version_py_path: str | PathLike) -> str:
    """Execute _version.py to get __version__."""
    return exec_version_py_to_get_version_dict(version_py_path)["version"]
