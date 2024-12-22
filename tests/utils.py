import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from shutil import rmtree

import pytest

from version_pioneer.utils.exec_version_py import (
    exec_version_py_code_to_get_version_dict,
    exec_version_py_to_get_version,
)

logger = logging.getLogger(__name__)


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


def assert_build_and_version_persistence(project_dir: Path):
    """
    Build a fake project end-to-end and verify wheel contents.

    First, do it with tag v0.1.0, then with a commit, then with unstaged changes (dirty).
    """
    dynamic_version = get_dynamic_version(project_dir)

    build_project()

    whl = project_dir / "dist" / "my_app-0.1.0-py3-none-any.whl"

    assert whl.exists(), f"Build did not produce a correctly named wheel. Found: {os.listdir(project_dir / 'dist')}"

    run("wheel", "unpack", whl)

    resolved_version_py = (
        project_dir / "my_app-0.1.0" / "my_app" / "_version.py"
    ).read_text()
    verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    logger.info(f"Resolved _version.py code: {resolved_version_py}")
    version_after_tag: str = exec_version_py_code_to_get_version_dict(
        resolved_version_py
    )["version"]
    logger.info(f"Version after tag: {version_after_tag}")

    assert version_after_tag == "0.1.0"
    assert version_after_tag == dynamic_version

    #############################################
    # the second build will have a different version.
    rmtree(project_dir / "dist")
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "commit", "-am", "Second commit"], cwd=project_dir, check=True
    )

    # ps = subprocess.run(
    #     ["git", "status"],
    #     cwd=new_hatchling_project,
    #     check=True,
    #     capture_output=True,
    #     text=True,
    # )
    # logger.info(ps.stdout)

    dynamic_version = get_dynamic_version(project_dir)
    logger.info(f"Version after one commit (dynamic): {dynamic_version}")

    assert dynamic_version != "0.1.0"
    assert dynamic_version.startswith("0.1.0+1.g")
    assert not dynamic_version.endswith(".dirty")

    build_project()

    # whls = list((new_hatchling_project / "dist").glob("*.whl"))
    # logger.info(f"Found wheels: {whls}")
    whl = project_dir / "dist" / f"my_app-{dynamic_version}-py3-none-any.whl"
    # ps = subprocess.run(
    #     ["git", "status"],
    #     cwd=project_dir,
    #     check=True,
    #     capture_output=True,
    #     text=True,
    # )
    # logger.info(ps.stdout)
    assert whl.exists(), f"Build did not produce a correctly named wheel. Found: {os.listdir(project_dir / 'dist')}"

    run("wheel", "unpack", whl)

    resolved_version_py = (
        project_dir / f"my_app-{dynamic_version}" / "my_app" / "_version.py"
    ).read_text()
    verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    version_after_commit_resolved = exec_version_py_code_to_get_version_dict(
        resolved_version_py
    )["version"]
    logger.info(f"Version after commit (resolved): {version_after_commit_resolved}")

    assert dynamic_version == version_after_commit_resolved

    #############################################
    # modify a file and see if .dirty is appended
    # only unstaged changes count, and not a new file. So we remove what we added earlier.
    rmtree(project_dir / "my_app-0.1.0")

    ps = subprocess.run(
        ["git", "status"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(ps.stdout)

    dynamic_version = get_dynamic_version(project_dir)
    logger.info(
        f"Version after one commit and unstaged changes (dynamic): {dynamic_version}"
    )

    assert dynamic_version != "0.1.0"
    assert dynamic_version.startswith("0.1.0+1.g")
    assert dynamic_version.endswith(".dirty")

    build_project()

    # whls = list((new_hatchling_project / "dist").glob("*.whl"))
    # logger.info(f"Found wheels: {whls}")
    whl = project_dir / "dist" / f"my_app-{dynamic_version}-py3-none-any.whl"
    assert whl.exists(), f"Build did not produce a correctly named wheel. Found: {os.listdir(project_dir / 'dist')}"

    run("wheel", "unpack", whl)

    resolved_version_py = (
        project_dir / f"my_app-{dynamic_version}" / "my_app" / "_version.py"
    ).read_text()
    verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    version_after_commit_resolved = exec_version_py_code_to_get_version_dict(
        resolved_version_py
    )["version"]
    logger.info(
        f"Version after commit and unstaged changes (resolved): {version_after_commit_resolved}"
    )

    assert dynamic_version == version_after_commit_resolved
