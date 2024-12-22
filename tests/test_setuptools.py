import logging
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.utils import (
    VersionPyResolutionError,
    assert_build_and_version_persistence,
    assert_build_consistency,
)

from .build_helpers import check_no_versionfile_build
from .utils import build_project

logger = logging.getLogger(__name__)


def test_build_consistency(new_setuptools_project: Path):
    assert_build_consistency(cwd=new_setuptools_project)


def test_build_version(new_setuptools_project: Path):
    assert_build_and_version_persistence(new_setuptools_project)


def test_invalid_config(new_setuptools_project: Path, plugin_wheel: Path):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    pyp = new_setuptools_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["setuptools", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "setuptools.build_meta"

            [tool.version-pioneer]
            # versionfile-source = "src/my_app/_version.py"
            # versionfile-build = "my_app/_version.py"

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
            versionfile-build = "my_app/_version.py"

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


@pytest.mark.xfail(raises=VersionPyResolutionError)
def test_no_versionfile_build(new_setuptools_project: Path, plugin_wheel: Path):
    """
    If versionfile-build is not configured, the build does NOT FAIL but the _version.py file is not updated.
    """
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_setuptools_project, check=True)
    subprocess.run(
        ["git", "checkout", "v0.1.0"], cwd=new_setuptools_project, check=True
    )

    pyp = new_setuptools_project / "pyproject.toml"

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["setuptools", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "setuptools.build_meta"

            [tool.version-pioneer]
            versionfile-source = "src/my_app/_version.py"
            # versionfile-build = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
    )

    # Can't use dynamic versioning without versionfile-build.
    setup_py = new_setuptools_project / "setup.py"
    setup_py.write_text(
        textwrap.dedent("""
            from setuptools import setup
            from version_pioneer.build.setuptools import get_cmdclass

            setup(
                version="0.1.1",
                cmdclass=get_cmdclass(),
            )
        """),
    )

    check_no_versionfile_build(cwd=new_setuptools_project)
