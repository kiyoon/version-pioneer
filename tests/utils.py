from __future__ import annotations

import filecmp
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from version_pioneer.utils.exec_version_py import (
    exec_version_py_to_get_version,
)

logger = logging.getLogger(__name__)


class VersionPyResolutionError(Exception):
    pass


def run(*args, check=True):
    """
    Run python module like `python -m ...`.
    """
    process = subprocess.run(  # noqa: PLW1510
        [sys.executable, "-m", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if check and process.returncode:
        pytest.fail(process.stdout)

    return process.stdout


def build_project(*args, cwd=None, check=True):
    """
    By default, build both wheel and sdist. And just check the content of the wheel later.

    If the wheel is built correctly this way, the sdist should be correct as well. (project dir -> sdist -> wheel)
    But if you build them separately, the sdist is skipped so we can't be sure.
    """
    # replace --out-dir with --outdir (pyproject-build uses --outdir)
    # NOTE: if you want to use pyproject-build, uncomment this.
    # args = (arg if arg != "--out-dir" else "--outdir" for arg in args)
    # return run("build", *args, check=check)

    process = subprocess.run(
        ["uv", "build", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
    )
    if check and process.returncode:
        pytest.fail(process.stderr)

    return process.stderr


def append(file, text):
    file.write_text(file.read_text() + text)


def _are_dir_trees_equal(dir1, dir2):
    """
    Compare two directories recursively. Files in each directory are
    assumed to be equal if their names and contents are equal.

    @param dir1: First directory path
    @param dir2: Second directory path

    @return: True if the directory trees are the same and
        there were no errors while accessing the directories or files,
        False otherwise.
    """
    dirs_cmp = filecmp.dircmp(dir1, dir2)
    if (
        len(dirs_cmp.left_only) > 0
        or len(dirs_cmp.right_only) > 0
        or len(dirs_cmp.funny_files) > 0
    ):
        return False
    (_, mismatch, errors) = filecmp.cmpfiles(
        dir1, dir2, dirs_cmp.common_files, shallow=False
    )
    if len(mismatch) > 0 or len(errors) > 0:
        return False
    for common_dir in dirs_cmp.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)
        new_dir2 = os.path.join(dir2, common_dir)
        if not _are_dir_trees_equal(new_dir1, new_dir2):
            return False
    return True


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
