"""Tests for version_pioneer.utils.config module."""

import pytest

from version_pioneer.utils.config import (
    find_config_file,
    get_config_value,
    load_config,
    normalize_pyproject_dict_to_config,
)


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_prefers_version_pioneer_toml(self, tmp_path):
        """version-pioneer.toml takes precedence over pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.version-pioneer]\nversionscript = "pkg/_version.py"',
            encoding="utf-8",
        )
        (tmp_path / "version-pioneer.toml").write_text(
            'versionscript = "src/_version.py"', encoding="utf-8"
        )

        config_file = find_config_file(tmp_path)
        assert config_file.name == "version-pioneer.toml"

    def test_falls_back_to_pyproject(self, tmp_path):
        """Falls back to pyproject.toml when version-pioneer.toml doesn't exist."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.version-pioneer]\nversionscript = "pkg/_version.py"',
            encoding="utf-8",
        )

        config_file = find_config_file(tmp_path)
        assert config_file.name == "pyproject.toml"

    def test_bypasses_pyproject_without_section(self, tmp_path):
        """pyproject.toml without [tool.version-pioneer] is skipped."""
        # Create parent dir with valid config
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / "version-pioneer.toml").write_text(
            'versionscript = "src/_version.py"', encoding="utf-8"
        )

        # Create child dir with pyproject.toml but no [tool.version-pioneer] section
        child = parent / "child"
        child.mkdir()
        (child / "pyproject.toml").write_text(
            '[project]\nname = "test"', encoding="utf-8"
        )

        # Should find the config in parent, not stop at child's pyproject.toml
        config_file = find_config_file(child)
        assert config_file == parent / "version-pioneer.toml"

    def test_finds_config_in_parent_when_child_has_empty_pyproject(self, tmp_path):
        """Finds config in parent when child has pyproject.toml without section."""
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / "pyproject.toml").write_text(
            '[tool.version-pioneer]\nversionscript = "src/_version.py"',
            encoding="utf-8",
        )

        child = parent / "child"
        child.mkdir()
        (child / "pyproject.toml").write_text(
            "[project]\nname = 'test'", encoding="utf-8"
        )

        config_file = find_config_file(child)
        assert config_file == parent / "pyproject.toml"

    def test_error_when_no_config_found(self, tmp_path):
        """Raises FileNotFoundError when no valid config exists."""
        # Create a pyproject.toml without the section
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"', encoding="utf-8"
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            find_config_file(tmp_path)

        assert "version-pioneer.toml" in str(exc_info.value)
        assert "[tool.version-pioneer]" in str(exc_info.value)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_version_pioneer_toml(self, tmp_path):
        """Config from version-pioneer.toml is loaded at root level."""
        (tmp_path / "version-pioneer.toml").write_text(
            'versionscript = "src/_version.py"\nversionfile-sdist = "src/_version.py"',
            encoding="utf-8",
        )

        result = load_config(tmp_path)

        assert result.source == "version-pioneer.toml"
        assert result.config["versionscript"] == "src/_version.py"
        assert result.config["versionfile-sdist"] == "src/_version.py"
        assert result.project_root == tmp_path
        assert result.config_file == tmp_path / "version-pioneer.toml"

    def test_load_pyproject_toml(self, tmp_path):
        """Config from pyproject.toml is extracted from [tool.version-pioneer]."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.version-pioneer]\nversionscript = "pkg/_version.py"',
            encoding="utf-8",
        )

        result = load_config(tmp_path)

        assert result.source == "pyproject.toml"
        assert result.config["versionscript"] == "pkg/_version.py"
        assert result.project_root == tmp_path

    def test_pyproject_with_empty_section(self, tmp_path):
        """pyproject.toml with empty [tool.version-pioneer] section is still valid."""
        (tmp_path / "pyproject.toml").write_text(
            "[tool.version-pioneer]", encoding="utf-8"
        )

        result = load_config(tmp_path)

        assert result.source == "pyproject.toml"
        assert result.config == {}


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_get_existing_key(self):
        """Returns value when key exists."""
        config = {"versionscript": "src/_version.py"}

        value = get_config_value(config, "versionscript")
        assert value == "src/_version.py"

    def test_get_missing_key_with_default(self):
        """Returns default when key is missing."""
        config = {}

        value = get_config_value(config, "versionscript", default="default.py")
        assert value == "default.py"

    def test_get_missing_key_raises_error(self):
        """Raises KeyError when key is missing and raise_error=True."""
        config = {}

        with pytest.raises(KeyError) as exc_info:
            get_config_value(
                config, "versionscript", raise_error=True, config_source="test.toml"
            )

        assert "versionscript" in str(exc_info.value)
        assert "test.toml" in str(exc_info.value)

    def test_return_path_object(self):
        """Returns Path object when return_path_object=True."""
        from pathlib import Path

        config = {"versionscript": "src/_version.py"}

        value = get_config_value(config, "versionscript", return_path_object=True)
        assert isinstance(value, Path)
        assert str(value) == "src/_version.py"

    def test_return_none_for_missing_key_with_path_object(self):
        """Returns None (not Path) when key is missing even with return_path_object=True."""
        config = {}

        value = get_config_value(config, "versionscript", return_path_object=True)
        assert value is None

    def test_default_and_raise_error_mutually_exclusive(self):
        """Raises ValueError when both default and raise_error are set."""
        config = {}

        with pytest.raises(ValueError):
            get_config_value(config, "key", default="value", raise_error=True)


class TestNormalizePyprojectDictToConfig:
    """Tests for normalize_pyproject_dict_to_config function."""

    def test_extracts_version_pioneer_section(self):
        """Extracts [tool.version-pioneer] section from pyproject dict."""
        pyproject = {
            "project": {"name": "test"},
            "tool": {
                "version-pioneer": {"versionscript": "src/_version.py"},
                "other-tool": {},
            },
        }

        config = normalize_pyproject_dict_to_config(pyproject)
        assert config == {"versionscript": "src/_version.py"}

    def test_returns_empty_dict_when_section_missing(self):
        """Returns empty dict when [tool.version-pioneer] section is missing."""
        pyproject = {"project": {"name": "test"}}

        config = normalize_pyproject_dict_to_config(pyproject)
        assert config == {}

    def test_returns_empty_dict_when_tool_section_missing(self):
        """Returns empty dict when [tool] section is missing."""
        pyproject = {"project": {"name": "test"}}

        config = normalize_pyproject_dict_to_config(pyproject)
        assert config == {}
