import logging
import subprocess
import textwrap
from pathlib import Path

import pytest

from .build_pipelines import (
    assert_build_and_version_persistence,
    assert_build_consistency,
    check_no_versionfile_build,
)
from .utils import (
    VersionPyResolutionError,
    build_project,
)

logger = logging.getLogger(__name__)


def test_build_consistency(new_hatchling_project: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_hatchling_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_hatchling_project, check=True)
    assert_build_consistency(cwd=new_hatchling_project)


def test_build_version(new_hatchling_project: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_hatchling_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_hatchling_project, check=True)
    assert_build_and_version_persistence(new_hatchling_project)


def test_invalid_config(new_hatchling_project: Path, plugin_wheel: Path):
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
            requires = ["hatchling", "version-pioneer @ {plugin_wheel.as_uri()}"]
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

    err = build_project(check=False)

    assert (
        "KeyError: 'Missing key tool.version-pioneer.versionfile-source in pyproject.toml'"
        in err
    ), err

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            # versionfile-source = "src/my_app/_version.py"
            versionfile-build = "src/my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
    )

    err = build_project(check=False)

    assert (
        "KeyError: 'Missing key tool.version-pioneer.versionfile-source in pyproject.toml'"
        in err
    ), err

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            # THE TWO MUST BE THE SAME WITH HATCHLING
            versionfile-source = "src/my_app/_version.py"
            versionfile-build = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
    )

    err = build_project(check=False)

    assert (
        "ValueError: For hatchling backend, versionfile-build must be the same as versionfile-source."
        in err
    ), err


@pytest.mark.xfail(raises=VersionPyResolutionError)
def test_no_versionfile_build(new_hatchling_project: Path, plugin_wheel: Path):
    """
    If versionfile-build is not configured, the build does NOT FAIL but the _version.py file is not updated.
    """
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_hatchling_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_hatchling_project, check=True)

    pyp = new_hatchling_project / "pyproject.toml"

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            versionfile-source = "src/my_app/_version.py"
            # versionfile-build = "src/my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
    )

    check_no_versionfile_build(cwd=new_hatchling_project)
