from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # NOTE: importing from version_pioneer._version is dangerous because it gets replaced to a constant during build.
    # So, we import from version_pioneer._version only in TYPE_CHECKING mode.
    from version_pioneer._version import VersionDict


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
