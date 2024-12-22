import re
import subprocess
import sys
from pathlib import Path

import pytest

from version_pioneer.utils.exec_version_py import exec_version_py_to_get_version


class VersionPyResolutionError(Exception):
    pass


def run(*args, check=True):
    process = subprocess.run(  # noqa: PLW1510
        [sys.executable, "-m", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if check and process.returncode:
        pytest.fail(process.stdout)

    return process.stdout


def build_project(*args, check=True):
    if not args:
        args = ["-w"]

    return run("build", *args, check=check)


def append(file, text):
    file.write_text(file.read_text() + text)


def verify_resolved_version_py(resolved_version_py_code: str):
    # does it have `__version_dict__ = { ... }`?
    if (
        re.search(
            r"^__version_dict__ = \{.*\}$", resolved_version_py_code, re.MULTILINE
        )
        is None
    ):
        raise VersionPyResolutionError(
            f"Resolved _version.py code does not contain __version_dict__ = {{ ... }}: {resolved_version_py_code}"
        )
    # and `__version__ = __version_dict__[...]`?
    if (
        re.search(
            r"^__version__ = __version_dict__\[.*\]$",
            resolved_version_py_code,
            re.MULTILINE,
        )
        is None
    ):
        raise VersionPyResolutionError(
            f"Resolved _version.py code does not contain __version__ = __version_dict__[...]: {resolved_version_py_code}"
        )


def get_dynamic_version(project_dir: Path) -> str:
    version_module_code = project_dir / "src" / "my_app" / "_version.py"
    return exec_version_py_to_get_version(version_module_code)
