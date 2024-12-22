import logging
import subprocess
import textwrap
from pathlib import Path
from shutil import rmtree

import pytest

from version_pioneer import get_version_py_path
from version_pioneer.utils.exec_version_py import (
    exec_version_py_code_to_get_version_dict,
)

from .utils import (
    VersionPyResolutionError,
    build_project,
    get_dynamic_version,
    run,
    verify_resolved_version_py,
)

logger = logging.getLogger(__name__)


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

    dynamic_version = get_dynamic_version(new_hatchling_project)

    build_project()

    whl = new_hatchling_project / "dist" / "my_app-0.1.0-py2.py3-none-any.whl"

    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_hatchling_project / "my_app-0.1.0" / "my_app" / "_version.py"
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

    dynamic_version = get_dynamic_version(new_hatchling_project)
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
    rmtree(new_hatchling_project / "my_app-0.1.0")

    ps = subprocess.run(
        ["git", "status"],
        cwd=new_hatchling_project,
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(ps.stdout)

    dynamic_version = get_dynamic_version(new_hatchling_project)
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
    verify_resolved_version_py(resolved_version_py)

    # actually evaluate the version
    version_after_commit_resolved = exec_version_py_code_to_get_version_dict(
        resolved_version_py
    )["version"]
    logger.info(
        f"Version after commit and unstaged changes (resolved): {version_after_commit_resolved}"
    )

    assert dynamic_version == version_after_commit_resolved


def test_invalid_config(new_hatchling_project: Path, plugin_dir: Path):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_hatchling_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_hatchling_project, check=True)

    pyp = new_hatchling_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_dir.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            # MISSING CONFIGURATION

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
    )

    out = build_project(check=False)

    assert (
        "KeyError: 'Missing key tool.version-pioneer.versionfile-source in pyproject.toml'"
        in out
    ), out

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_dir.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            # versionfile-source = "src/my_app/_version.py"
            versionfile-build = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
    )

    out = build_project(check=False)

    assert (
        "KeyError: 'Missing key tool.version-pioneer.versionfile-source in pyproject.toml'"
        in out
    ), out


@pytest.mark.xfail(raises=VersionPyResolutionError)
def test_no_versionfile_build(new_hatchling_project: Path, plugin_dir: Path):
    """
    If versionfile-build is not configured, the build does NOT FAIL but the _version.py file is not updated.
    """
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_hatchling_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_hatchling_project, check=True)

    pyp = new_hatchling_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_dir.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            versionfile-source = "src/my_app/_version.py"
            # versionfile-build = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
    )

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.1"], check=True)

    build_project(check=False)

    # logger.info(list((new_hatchling_project / "dist").glob("*")))
    whl = new_hatchling_project / "dist" / "my_app-0.1.1-py2.py3-none-any.whl"

    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_hatchling_project / "my_app-0.1.1" / "my_app" / "_version.py"
    ).read_text()
    assert resolved_version_py == get_version_py_path().read_text()
    verify_resolved_version_py(resolved_version_py)  # expected to fail
