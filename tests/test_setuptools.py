import logging
import textwrap
from pathlib import Path

from tests.utils import assert_build_and_version_persistence

from .utils import build_project

logger = logging.getLogger(__name__)


def test_build(new_setuptools_project: Path):
    assert_build_and_version_persistence(new_setuptools_project)


def test_invalid_config(new_setuptools_project: Path, plugin_dir: Path):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    pyp = new_setuptools_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["setuptools", "version-pioneer @ {plugin_dir.as_uri()}"]
            build-backend = "setuptools.build_meta"

            [tool.version-pioneer]
            # versionfile-source = "src/my_app/_version.py"
            # versionfile-build = "my_app/_version.py"

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
