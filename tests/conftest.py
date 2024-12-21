import shutil
import textwrap
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture(name="plugin_dir", scope="session")
def _plugin_dir():
    """
    Install the plugin into a temporary directory with a random path to
    prevent pip from caching it.

    Copy only the src directory, pyproject.toml, and whatever is needed
    to build ourselves.
    """
    with TemporaryDirectory() as d:
        directory = Path(d, "plugin")
        shutil.copytree(Path.cwd() / "src", directory / "src")
        shutil.copytree(Path.cwd() / "deps", directory / "deps")
        for fn in [
            "pyproject.toml",
            "LICENSE",
            "README.md",
            "hatch_build.py",
        ]:
            shutil.copy(Path.cwd() / fn, directory / fn)

        yield directory.resolve()


@pytest.fixture(name="new_hatchling_project")
def _new_hatchling_project(plugin_dir: Path, tmp_path: Path, monkeypatch):
    """
    Create, and cd into, a blank new project that is configured to use our temporary plugin installation.
    """
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    project_file = project_dir / "pyproject.toml"
    project_file.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_dir.as_uri()}"]
            build-backend = "hatchling.build"

            [project]
            name = "my-app"
            dynamic = ["version"]

            [tool.version-pioneer]
            version-py-path = "src/my_app/_version.py"

            [tool.hatch.version]
            source = "code"
            path = "src/my_app/_version.py"

            [tool.hatch.build.hooks.version-pioneer]
        """),
        encoding="utf-8",
    )

    package_dir = project_dir / "src" / "my_app"
    package_dir.mkdir(parents=True)

    package_root = package_dir / "__init__.py"
    package_root.write_text("")

    version_file = package_dir / "_version.py"
    copy2(plugin_dir / "src" / "version_pioneer" / "_version.py", version_file)

    monkeypatch.chdir(project_dir)

    return project_dir
