import logging
import subprocess
import textwrap
from pathlib import Path
from shutil import rmtree

import pytest

from tests.build_pipelines import (
    assert_build_and_version_persistence,
)
from tests.utils import (
    VersionScriptResolutionError,
)
from version_pioneer.api import (
    build_consistency_test,
)
from version_pioneer.utils.build import build_project

from .build_pipelines import check_no_versionfile_output

logger = logging.getLogger(__name__)


def test_build_consistency(new_setuptools_project: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_setuptools_project, check=True)
    subprocess.run(
        ["git", "checkout", "v0.1.0"], cwd=new_setuptools_project, check=True
    )
    build_consistency_test(project_dir=new_setuptools_project, expected_version="0.1.0")


def test_build_version(new_setuptools_project: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_setuptools_project, check=True)
    subprocess.run(
        ["git", "checkout", "v0.1.0"], cwd=new_setuptools_project, check=True
    )
    assert_build_and_version_persistence(new_setuptools_project)


def test_different_versionfile(new_setuptools_project: Path, plugin_wheel: Path):
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
            versionscript = "src/my_app/_version.py"
            versionfile-sdist = "src/my_app/_versionfile.py"
            versionfile-wheel = "my_app/_versionfile.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
    )

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.1"], check=True)

    build_consistency_test(project_dir=new_setuptools_project, expected_version="0.1.1")


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
            # versionscript = "src/my_app/_version.py"
            # versionfile-sdist = "src/my_app/_version.py"
            # versionfile-wheel = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
    )

    err, _ = build_project(check=False)

    assert (
        "KeyError: 'Missing key tool.version-pioneer.versionscript in pyproject.toml'"
        in err
    ), err

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["setuptools", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "setuptools.build_meta"

            [tool.version-pioneer]
            # versionscript = "src/my_app/_version.py"
            versionfile-sdist = "src/my_app/_version.py"
            # versionfile-wheel = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
    )

    err, _ = build_project(check=False)

    assert (
        "KeyError: 'Missing key tool.version-pioneer.versionscript in pyproject.toml'"
        in err
    ), err


@pytest.mark.xfail(raises=VersionScriptResolutionError)
def test_no_versionfile_sdist_nor_wheel(
    new_setuptools_project: Path, plugin_wheel: Path
):
    """
    If versionfile-sdist and versionfile-wheel is not configured, the build does NOT FAIL
    but the _version.py file is not updated.
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
            versionscript = "src/my_app/_version.py"
            # versionfile-sdist = "src/my_app/_version.py"
            # versionfile-wheel = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
    )

    # Can't use dynamic versioning without versionfile-wheel.
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

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.1"], check=True)

    # The build should be consistent still, because versionfile-sdist and versionfile-wheel are both not configured.

    # NOTE: since we don't write the versionfile, we normally can't chain the tests.
    # However, hatchling actually reads PKG-INFO metadata in the sdist,
    # and if it's present, the version source is ignored.
    # In setuptools, the `get_version_dict()` includes this logic.
    temp_dir = build_consistency_test(
        project_dir=new_setuptools_project,
        test_chaining=True,
        delete_temp_dir=False,
        expected_version="0.1.1",
    )

    # No need to build again. We check the _version.py file directly on sdist and wheel.
    Path(temp_dir / "dist").rename(new_setuptools_project / "dist")
    rmtree(temp_dir)

    check_no_versionfile_output(cwd=new_setuptools_project)
