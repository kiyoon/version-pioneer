import os
import subprocess
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from version_pioneer.api import get_version_script_core_code
from version_pioneer.template import SETUP_PY
from version_pioneer.utils.build import build_project

SCRIPT_DIR = Path(__file__).resolve().parent
os.environ["GIT_CONFIG_GLOBAL"] = str(SCRIPT_DIR / "gitconfig")


# @pytest.fixture(name="plugin_dir", scope="session")
# def _plugin_dir():
#     """
#     Install the plugin into a temporary directory with a random path to
#     prevent pip from caching it.
#
#     Copy only the src directory, pyproject.toml, and whatever is needed
#     to build ourselves.
#     """
#     with TemporaryDirectory() as d:
#         directory = Path(d, "plugin")
#         shutil.copytree(Path.cwd() / "src", directory / "src")
#         shutil.copytree(Path.cwd() / "deps", directory / "deps")
#         # required because this plugin uses git to get version
#         shutil.copytree(Path.cwd() / ".git", directory / ".git")
#         for fn in [
#             "pyproject.toml",
#             "LICENSE",
#             "README.md",
#             "hatch_build.py",
#         ]:
#             shutil.copy(Path.cwd() / fn, directory / fn)
#
#         yield directory.resolve()


@pytest.fixture(name="plugin_wheel", scope="session")
def _plugin_wheel():
    """
    Build the plugin into a temporary directory with a random path to
    prevent pip from caching it.

    Instead of above approach that copies the source code, building the plugin
    ensures that the plugin is built correctly for deployment.

    For example, it ensures _version.py and _version_orig.py are included in the wheel with different content.
    """
    with TemporaryDirectory() as d:
        out, builds = build_project("--out-dir", d)
        assert len(builds) == 2
        wheel_path = builds[1]
        if not wheel_path.is_absolute():
            # pyproject-build does not print absolute path
            wheel_path = Path(d) / wheel_path

        yield wheel_path


@pytest.fixture(name="new_hatchling_project")
def _new_hatchling_project(plugin_wheel: Path, tmp_path: Path, monkeypatch):
    """
    Create, and cd into, a blank new project that is configured to use our temporary plugin installation.
    """
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    pyproject_file = project_dir / "pyproject.toml"
    pyproject_file.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["hatchling", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "hatchling.build"

            [tool.hatch.version]
            source = "version-pioneer"

            [tool.hatch.build.hooks.version-pioneer]

            [tool.version-pioneer]
            versionscript = "src/my_app/_version.py"
            versionfile-sdist = "src/my_app/_version.py"
            versionfile-wheel = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
        encoding="utf-8",
    )

    package_dir = project_dir / "src" / "my_app"
    package_dir.mkdir(parents=True)

    # NOTE: without gitignore, build will create artifacts which makes the version always dirty,
    # and include wrong files in the package
    gitignore_file = project_dir / ".gitignore"
    gitignore_file.write_text(
        textwrap.dedent("""
            /dist/
            /dist-*/
        """)
    )

    package_root = package_dir / "__init__.py"
    package_root.write_text("")

    version_file = package_dir / "_version.py"
    version_file.write_text(get_version_script_core_code())

    monkeypatch.chdir(project_dir)

    assert Path.cwd() == project_dir

    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0"], check=True)

    return project_dir


@pytest.fixture(name="new_setuptools_project")
def _new_setuptools_project(plugin_wheel: Path, tmp_path: Path, monkeypatch):
    """
    Create, and cd into, a blank new project that is configured to use our temporary plugin installation.
    """
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    pyproject_file = project_dir / "pyproject.toml"
    pyproject_file.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["setuptools", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "setuptools.build_meta"

            [tool.version-pioneer]
            versionscript = "src/my_app/_version.py"
            versionfile-sdist = "src/my_app/_version.py"
            versionfile-wheel = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
        encoding="utf-8",
    )

    setup_file = project_dir / "setup.py"
    setup_file.write_text(SETUP_PY)

    # NOTE: without gitignore, build will create artifacts which makes the version always dirty
    gitignore_file = project_dir / ".gitignore"
    gitignore_file.write_text(
        textwrap.dedent("""
            *.egg-info/
            /dist/
            /dist-*/
        """)
    )

    package_dir = project_dir / "src" / "my_app"
    package_dir.mkdir(parents=True)

    package_root = package_dir / "__init__.py"
    package_root.write_text("")

    version_file = package_dir / "_version.py"
    version_file.write_text(get_version_script_core_code())

    monkeypatch.chdir(project_dir)

    assert Path.cwd() == project_dir

    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0"], check=True)

    return project_dir


@pytest.fixture(name="new_pdm_project")
def _new_pdm_project(plugin_wheel: Path, tmp_path: Path, monkeypatch):
    """
    Create, and cd into, a blank new project that is configured to use our temporary plugin installation.
    """
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    pyproject_file = project_dir / "pyproject.toml"
    pyproject_file.write_text(
        textwrap.dedent(f"""
            [build-system]
            requires = ["pdm-backend", "version-pioneer @ {plugin_wheel.as_uri()}"]
            build-backend = "pdm.backend"

            [tool.version-pioneer]
            versionscript = "src/my_app/_version.py"
            versionfile-sdist = "src/my_app/_version.py"
            versionfile-wheel = "my_app/_version.py"

            [project]
            name = "my-app"
            dynamic = ["version"]
            requires-python = ">=3.8"
        """),
        encoding="utf-8",
    )

    # NOTE: without gitignore, build will create artifacts which makes the version always dirty
    gitignore_file = project_dir / ".gitignore"
    gitignore_file.write_text(
        textwrap.dedent("""
            /dist/
            /dist-*/
        """)
    )

    package_dir = project_dir / "src" / "my_app"
    package_dir.mkdir(parents=True)

    package_root = package_dir / "__init__.py"
    package_root.write_text("")

    version_file = package_dir / "_version.py"
    version_file.write_text(get_version_script_core_code())

    monkeypatch.chdir(project_dir)

    assert Path.cwd() == project_dir

    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0"], check=True)

    return project_dir
