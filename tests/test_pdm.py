import logging
import subprocess
import textwrap
from pathlib import Path

import pytest

from version_pioneer.api import build_consistency_test
from version_pioneer.utils.build import build_project

from .build_pipelines import (
    assert_build_and_version_persistence,
    check_no_versionfile_output,
)
from .utils import (
    VersionScriptResolutionError,
)

logger = logging.getLogger(__name__)


def test_build_consistency(new_pdm_project: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_pdm_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_pdm_project, check=True)
    build_consistency_test(project_dir=new_pdm_project)


def test_build_version(new_pdm_project: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_pdm_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_pdm_project, check=True)
    assert_build_and_version_persistence(new_pdm_project)


def test_different_versionfile(new_pdm_project: Path, plugin_wheel: Path):
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_pdm_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_pdm_project, check=True)

    pyp = new_pdm_project / "pyproject.toml"

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["pdm-backend", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "pdm.backend"

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

    build_consistency_test(project_dir=new_pdm_project, expected_version="0.1.1")


def test_invalid_config(new_pdm_project: Path, plugin_wheel: Path):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_pdm_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_pdm_project, check=True)

    pyp = new_pdm_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["pdm-backend", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "pdm.backend"

            [tool.version-pioneer]
            # MISSING CONFIGURATION

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

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["pdm-backend", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "pdm.backend"

            [tool.version-pioneer]
            # versionscript = "src/my_app/_version.py"
            versionfile-sdist = "src/my_app/_version.py"
            versionfile-wheel = "my_app/_version.py"

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
def test_no_versionfile_sdist(new_pdm_project: Path, plugin_wheel: Path):
    """
    If versionfile-sdist is not configured, the build does NOT FAIL but the _version.py file is not updated.
    """
    # Reset the project to a known state.
    subprocess.run(["git", "stash", "--all"], cwd=new_pdm_project, check=True)
    subprocess.run(["git", "checkout", "v0.1.0"], cwd=new_pdm_project, check=True)

    pyp = new_pdm_project / "pyproject.toml"

    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["pdm-backend", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "pdm.backend"

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

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.1"], check=True)

    # NOTE: consistency check fails on PDM because when building both sdist and wheel at the same time,
    # the wheel is built from the sdist, and the sdist doesn't have git information because we do not change
    # the versionfile.
    # This is rather expected, because the user specifically asked to not update the versionfile.
    # This works in hatchling because they provide a way to execute the version script directly.
    # It's just a minor difference in how they work, which should be noted, but it's not a bug.
    # You just made a wrong sdist, because sdist has to be complete and self-contained.
    # assert_build_consistency(version="0.1.1", cwd=new_pdm_project)  # Fails here.

    # Instead, we build the sdist and wheel separately.
    build_project("--sdist", cwd=new_pdm_project)
    build_project("--wheel", cwd=new_pdm_project)

    check_no_versionfile_output(cwd=new_pdm_project)
