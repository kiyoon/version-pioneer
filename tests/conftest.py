import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

import pytest

from version_pioneer import get_version_py_path
from version_pioneer.template import SETUP_PY

SCRIPT_DIR = Path(__file__).resolve().parent
os.environ["GIT_CONFIG_GLOBAL"] = str(SCRIPT_DIR / "gitconfig")


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

    pyproject_file = project_dir / "pyproject.toml"
    pyproject_file.write_text(
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
            versionfile-build = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
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

    assert Path.cwd() == project_dir

    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0"], check=True)

    return project_dir


@pytest.fixture(name="new_setuptools_project")
def _new_setuptools_project(plugin_dir: Path, tmp_path: Path, monkeypatch):
    """
    Create, and cd into, a blank new project that is configured to use our temporary plugin installation.
    """
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    pyproject_file = project_dir / "pyproject.toml"
    pyproject_file.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["setuptools", "version-pioneer @ {plugin_dir.as_uri()}"]
            build-backend = "setuptools.build_meta"

            [tool.version-pioneer]
            versionfile-source = "src/my_app/_version.py"
            versionfile-build = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
        """),
        encoding="utf-8",
    )

    setup_file = project_dir / "setup.py"
    setup_file.write_text(SETUP_PY)

    package_dir = project_dir / "src" / "my_app"
    package_dir.mkdir(parents=True)

    package_root = package_dir / "__init__.py"
    package_root.write_text("")

    version_file = package_dir / "_version.py"
    copy2(get_version_py_path(), version_file)

    monkeypatch.chdir(project_dir)

    assert Path.cwd() == project_dir

    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0"], check=True)

    return project_dir
