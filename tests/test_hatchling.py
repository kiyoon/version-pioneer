import logging
import subprocess
import textwrap
from pathlib import Path

import pytest

from version_pioneer import get_version_py_path

from .utils import (
    VersionPyResolutionError,
    assert_build_and_version_persistence,
    build_project,
    run,
    verify_resolved_version_py,
)

logger = logging.getLogger(__name__)


def test_build(new_hatchling_project: Path):
    assert_build_and_version_persistence(new_hatchling_project)


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
