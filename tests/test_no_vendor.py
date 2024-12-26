import textwrap
from pathlib import Path

import pytest

from version_pioneer.template import NO_VENDOR_VERSIONSCRIPT
from version_pioneer.utils.build import build_project
from version_pioneer.utils.version_script import exec_version_script


def test_no_vendor_hatchling_parentdir_prefix_from_url(
    plugin_wheel: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """
    Using default NO_VENDOR_VERSIONSCRIPT template, version should be inferred from parent directory.
    """
    project_dir = tmp_path / "no_vendor_hatchling_project-0.7.0"
    project_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(project_dir)

    pyp = project_dir / "pyproject.toml"

    pyp.write_text(
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
            name = "kkkkkkk"  # <- NOT HERE
            dynamic = ["version"]
            requires-python = ">=3.8"

            [project.urls]
            source = "https://github.com/username/no_vendor_hatchling_project.git"  # <- HERE
        """)
    )

    (project_dir / "src" / "my_app").mkdir(parents=True, exist_ok=True)
    (project_dir / "src" / "my_app" / "_version.py").write_text(NO_VENDOR_VERSIONSCRIPT)

    version_dict = exec_version_script(project_dir / "src" / "my_app" / "_version.py")
    assert version_dict["version"] == "0.7.0"

    out, built_paths = build_project()
    assert len(built_paths) == 2
    assert "Successfully built dist/kkkkkkk-0.7.0-py3-none-any.whl" in out
    assert "Successfully built dist/kkkkkkk-0.7.0.tar.gz" in out


def test_no_vendor_hatchling_parentdir_prefix_from_project_name(
    plugin_wheel: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """
    Using default NO_VENDOR_VERSIONSCRIPT template, version should be inferred from parent directory.
    """
    project_dir = tmp_path / "infer-from-project-name-0.0.5"
    project_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(project_dir)

    pyp = project_dir / "pyproject.toml"

    pyp.write_text(
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
            name = "infer-from-project-name"  # <- HERE
            dynamic = ["version"]
            requires-python = ">=3.8"

            # [project.urls] does not exist
        """)
    )

    (project_dir / "src" / "my_app").mkdir(parents=True, exist_ok=True)
    (project_dir / "src" / "my_app" / "_version.py").write_text(NO_VENDOR_VERSIONSCRIPT)

    version_dict = exec_version_script(project_dir / "src" / "my_app" / "_version.py")
    assert version_dict["version"] == "0.0.5"

    out, built_paths = build_project()
    assert len(built_paths) == 2
    assert (
        "Successfully built dist/infer_from_project_name-0.0.5-py3-none-any.whl" in out
    )
    assert "Successfully built dist/infer_from_project_name-0.0.5.tar.gz" in out
