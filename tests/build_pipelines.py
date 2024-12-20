"""
Once the package is set up, run the following commands to build the package.

It should be compatible with multiple build backends.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from shutil import rmtree

from tests.utils import (
    get_dynamic_version,
    verify_resolved_versionfile,
)
from version_pioneer.api import get_version_script_core_code
from version_pioneer.utils.build import build_project, unpack_wheel
from version_pioneer.utils.version_script import (
    exec_version_script_code,
)

logger = logging.getLogger(__name__)


def assert_build_and_version_persistence(project_dir: Path):
    """
    Build a fake project end-to-end and verify wheel contents.

    First, do it with tag v0.1.0, then with a commit, then with unstaged changes (dirty).
    """
    dynamic_version = get_dynamic_version(project_dir)

    build_project(cwd=project_dir)

    whl = project_dir / "dist" / "my_app-0.1.0-py3-none-any.whl"

    assert whl.exists(), f"Build did not produce a correctly named wheel. Found: {os.listdir(project_dir / 'dist')}"

    unpack_wheel(whl)

    resolved_versionfile = (
        project_dir / "my_app-0.1.0" / "my_app" / "_version.py"
    ).read_text()
    verify_resolved_versionfile(resolved_versionfile)

    # actually evaluate the version
    logger.info(f"Resolved _version.py code: {resolved_versionfile}")
    version_after_tag: str = exec_version_script_code(resolved_versionfile)["version"]
    logger.info(f"Version after tag: {version_after_tag}")

    assert version_after_tag == "0.1.0"
    assert version_after_tag == dynamic_version

    #############################################
    # the second build will have a different version.
    rmtree(project_dir / "dist")
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-am", "Second commit"],
        cwd=project_dir,
        check=True,
    )

    ps = subprocess.run(
        ["git", "status"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(ps.stdout)

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

    unpack_wheel(whl)

    resolved_versionfile = (
        project_dir / f"my_app-{dynamic_version}" / "my_app" / "_version.py"
    ).read_text()
    verify_resolved_versionfile(resolved_versionfile)

    # actually evaluate the version
    version_after_commit_resolved = exec_version_script_code(resolved_versionfile)[
        "version"
    ]
    logger.info(f"Version after commit (resolved): {version_after_commit_resolved}")

    assert dynamic_version == version_after_commit_resolved

    #############################################
    # modify a file and see if .dirty is appended
    # only unstaged changes count, and not a new file. So we remove what we added earlier.
    rmtree(project_dir / "my_app-0.1.0")
    (project_dir / "aaa.txt").touch()
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)

    # ps = subprocess.run(
    #     ["git", "status"],
    #     cwd=project_dir,
    #     check=True,
    #     capture_output=True,
    #     text=True,
    # )
    # logger.info(ps.stdout)

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

    unpack_wheel(whl)

    resolved_versionfile = (
        project_dir / f"my_app-{dynamic_version}" / "my_app" / "_version.py"
    ).read_text()
    verify_resolved_versionfile(resolved_versionfile)

    # actually evaluate the version
    version_after_commit_resolved = exec_version_script_code(resolved_versionfile)[
        "version"
    ]
    logger.info(
        f"Version after commit and unstaged changes (resolved): {version_after_commit_resolved}"
    )

    assert dynamic_version == version_after_commit_resolved


def check_no_versionfile_output(*, cwd: Path, mode: str = "both", version="0.1.1"):
    """
    Check when versionfile-sdist or versionfile-wheel is not set.

    Note:
        Must be used with xfail(raise=VersionScriptResolutionError).

    Assume dist/ exists and contains the built files.
    """
    if mode not in ("sdist", "wheel", "both"):
        raise ValueError(f"Invalid mode: {mode}")
    if mode in ("sdist", "both"):
        sdist = cwd / "dist" / f"my_app-{version}.tar.gz"
        assert sdist.exists()
        subprocess.run(["tar", "xzf", sdist], cwd=cwd / "dist", check=True)
        unresolved_versionscript = (
            cwd / "dist" / f"my_app-{version}" / "src" / "my_app" / "_version.py"
        ).read_text()
        assert unresolved_versionscript == get_version_script_core_code()
        verify_resolved_versionfile(unresolved_versionscript)  # expected to fail
    if mode in ("wheel", "both"):
        # logger.info(list((cwd / "dist").glob("*")))
        whl = cwd / "dist" / f"my_app-{version}-py3-none-any.whl"

        assert whl.exists()

        unpack_wheel(whl, dest_dir=cwd / "dist")

        unresolved_versionscript = (
            cwd / "dist" / f"my_app-{version}" / "my_app" / "_version.py"
        ).read_text()
        assert unresolved_versionscript == get_version_script_core_code()
        verify_resolved_versionfile(unresolved_versionscript)  # expected to fail
    rmtree(cwd / "dist")
