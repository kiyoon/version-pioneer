from __future__ import annotations

import filecmp
import logging
import os
import re
import subprocess
import sys
from os import PathLike
from pathlib import Path
from shutil import copy2, rmtree

import pytest

from version_pioneer.utils.exec_version_py import (
    exec_version_py_code_to_get_version_dict,
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


def assert_build_consistency(version="0.1.0", cwd: str | PathLike | None = None):
    """
    The result of `build` can be different from running with --wheel and --sdist separately, so assure equality.

    This is because (I assume) when building both wheel and sdist, it first generates sdist (which should include all
    files necessary for the wheel), then builds the wheel from the sdist. If you build with `build --wheel` only, it
    processes the files from the git project directory directly. Thus, it is likely that `build` (both) fails to include
    version from git describe, while `build --wheel` does.

    Also, the _version.py gets resolved twice, once for the sdist, and once for the wheel. This can result in different
    outputs, thus we need to check the equality.
    """
    build_project("--wheel", "--out-dir", "dist-separated", cwd=cwd, check=True)
    build_project("--sdist", "--out-dir", "dist-separated", cwd=cwd, check=True)
    build_project("--out-dir", "dist-combined", cwd=cwd, check=True)

    if cwd is None:
        cwd = Path.cwd()
    else:
        cwd = Path(cwd)

    # compare the contents of the wheels
    separated = list((cwd / "dist-separated").glob("*.whl"))
    combined = list((cwd / "dist-combined").glob("*.whl"))
    assert len(separated) == 1
    assert len(combined) == 1
    separated = separated[0]
    combined = combined[0]
    assert separated.name == combined.name
    # copy2(separated, "/Users/kiyoon/my_app-{version}-py3-none-any.whl")
    # copy2(combined, "/Users/kiyoon/Downloads/my_app-{version}-py3-none-any.whl")

    # assert separated.read_bytes() == combined.read_bytes()  # this doesn't work as I thought.
    # The wheels can be different but the contents should be the same.
    run("wheel", "unpack", separated, "--dest", "dist-separated")
    run("wheel", "unpack", combined, "--dest", "dist-combined")
    assert _are_dir_trees_equal(
        cwd / f"dist-separated/my_app-{version}",
        cwd / f"dist-combined/my_app-{version}",
    )
    rmtree(cwd / "dist-separated" / f"my_app-{version}")
    rmtree(cwd / "dist-combined" / f"my_app-{version}")

    # compare two directories

    # compare the contents of the sdists
    separated = list((cwd / "dist-separated").glob("*.tar.gz"))
    combined = list((cwd / "dist-combined").glob("*.tar.gz"))
    assert len(separated) == 1
    assert len(combined) == 1
    separated = separated[0]
    combined = combined[0]
    assert separated.name == combined.name
    # copy2(separated, "/Users/kiyoon/my_app-{version}.tar.gz")
    # copy2(combined, "/Users/kiyoon/Downloads/my_app-{version}.tar.gz")

    # assert separated.read_bytes() == combined.read_bytes()  # this doesn't work as I thought.
    # maybe the order of files in the tarball is different, so we can't compare the bytes directly.
    subprocess.run(
        ["tar", "-xzf", separated, "--directory", "dist-separated"], check=True
    )
    subprocess.run(
        ["tar", "-xzf", combined, "--directory", "dist-combined"], check=True
    )
    assert _are_dir_trees_equal(
        cwd / f"dist-separated/my_app-{version}",
        cwd / f"dist-combined/my_app-{version}",
    )
    rmtree(cwd / "dist-separated" / f"my_app-{version}")
    rmtree(cwd / "dist-combined" / f"my_app-{version}")


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

    build_project(cwd=project_dir)

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

    build_project(cwd=project_dir)

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

    build_project(cwd=project_dir)

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
