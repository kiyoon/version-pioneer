import logging
import re
import subprocess
from pathlib import Path
from shutil import rmtree

import pytest

from .utils import run

logger = logging.getLogger(__name__)


def build_project(*args, check=True):
    if not args:
        args = ["-w"]

    return run("build", *args, check=check)


def _verify_resolved_version_py(resolved_version_py_code: str):
    # does it have `__version_dict__ = { ... }`?
    assert (
        re.search(
            r"^__version_dict__ = \{.*\}$", resolved_version_py_code, re.MULTILINE
        )
        is not None
    )
    # and `__version__ = __version_dict__[...]`?
    assert (
        re.search(
            r"^__version__ = __version_dict__\[.*\]$",
            resolved_version_py_code,
            re.MULTILINE,
        )
        is not None
    )


def _get_version_from_code(version_module_code: str) -> str:
    version_module_globals = {}
    exec(version_module_code, version_module_globals)
    return version_module_globals["__version__"]


def _get_dynamic_version(new_hatchling_project: Path) -> str:
    version_module_globals = {}
    version_module_code = (
        new_hatchling_project / "src" / "my_app" / "_version.py"
    ).read_text()
    exec(version_module_code, version_module_globals)
    return version_module_globals["__version__"]


def test_build(new_hatchling_project: Path):
    """
    Build a fake project end-to-end and verify wheel contents.

    First, do it with tag v0.1.0, then with a commit, then with unstaged changes (dirty).
    """
    #     append(
    #         new_project / "pyproject.toml",
    #         """
    # [tool.hatch.build.hooks.version-pioneer]
    # """,
    #     )

    dynamic_version = _get_dynamic_version(new_hatchling_project)

    build_project()

    whl = new_hatchling_project / "dist" / "my_app-0.1.0-py2.py3-none-any.whl"

    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_hatchling_project / "my_app-0.1.0" / "my_app" / "_version.py"
    ).read_text()
    _verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    version_after_tag: str = _get_version_from_code(resolved_version_py)
    logger.info(f"Version after tag: {version_after_tag}")

    assert version_after_tag == "0.1.0"
    assert version_after_tag == dynamic_version

    #############################################
    # the second build will have a different version.
    rmtree(new_hatchling_project / "dist")
    subprocess.run(["git", "add", "."], cwd=new_hatchling_project, check=True)
    subprocess.run(
        ["git", "commit", "-am", "Second commit"], cwd=new_hatchling_project, check=True
    )

    # ps = subprocess.run(
    #     ["git", "status"],
    #     cwd=new_hatchling_project,
    #     check=True,
    #     capture_output=True,
    #     text=True,
    # )
    # logger.info(ps.stdout)

    dynamic_version = _get_dynamic_version(new_hatchling_project)
    logger.info(f"Version after one commit (dynamic): {dynamic_version}")

    assert dynamic_version != "0.1.0"
    assert dynamic_version.startswith("0.1.0+1.g")

    build_project()

    # whls = list((new_hatchling_project / "dist").glob("*.whl"))
    # logger.info(f"Found wheels: {whls}")
    whl = (
        new_hatchling_project
        / "dist"
        / f"my_app-{dynamic_version}-py2.py3-none-any.whl"
    )
    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_hatchling_project / f"my_app-{dynamic_version}" / "my_app" / "_version.py"
    ).read_text()
    _verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    version_after_commit_resolved = _get_version_from_code(resolved_version_py)
    logger.info(f"Version after commit (resolved): {version_after_commit_resolved}")

    assert dynamic_version == version_after_commit_resolved

    #############################################
    # modify a file and see if .dirty is appended
    # only unstaged changes count, and not a new file. So we remove what we added earlier.
    rmtree(new_hatchling_project / "my_app-0.1.0")

    ps = subprocess.run(
        ["git", "status"],
        cwd=new_hatchling_project,
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(ps.stdout)

    dynamic_version = _get_dynamic_version(new_hatchling_project)
    logger.info(
        f"Version after one commit and unstaged changes (dynamic): {dynamic_version}"
    )

    assert dynamic_version != "0.1.0"
    assert dynamic_version.startswith("0.1.0+1.g")
    assert dynamic_version.endswith(".dirty")

    build_project()

    # whls = list((new_hatchling_project / "dist").glob("*.whl"))
    # logger.info(f"Found wheels: {whls}")
    whl = (
        new_hatchling_project
        / "dist"
        / f"my_app-{dynamic_version}-py2.py3-none-any.whl"
    )
    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_hatchling_project / f"my_app-{dynamic_version}" / "my_app" / "_version.py"
    ).read_text()
    _verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    version_after_commit_resolved = _get_version_from_code(resolved_version_py)
    logger.info(
        f"Version after commit and unstaged changes (resolved): {version_after_commit_resolved}"
    )

    assert dynamic_version == version_after_commit_resolved


def test_invalid_config(new_hatchling_project):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    pyp = new_hatchling_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(pyp.read_text() + "[tool.hatch.build.hooks.version-pioneer]")

    out = build_project(check=False)

    # assert "hatch_fancy_pypi_readme.exceptions.ConfigurationError" in out, out
    # assert (
    #     "tool.hatch.metadata.hooks.fancy-pypi-readme.content-type is missing." in out
    # ), out
    # assert (
    #     "tool.hatch.metadata.hooks.fancy-pypi-readme.fragments is missing." in out
    # ), out
