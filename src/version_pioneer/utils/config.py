from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any

from .toml import load_toml


@dataclass
class VersionPioneerConfigResult:
    """Result of finding and loading version-pioneer configuration."""

    config: dict[str, Any]  # Normalized config (without tool.version-pioneer prefix)
    config_file: Path  # Path to the config file used
    project_root: Path  # Project root directory
    source: str  # "version-pioneer.toml" or "pyproject.toml"


def find_config_file(project_dir: str | PathLike | None = None) -> Path:
    """
    Find the version-pioneer config file.

    Search algorithm (at each directory level, walking up to root):
    1. Check for version-pioneer.toml → if found, use it
    2. Check for pyproject.toml with [tool.version-pioneer] section → if found AND has section, use it
    3. If pyproject.toml exists but no section, continue to parent directory
    4. Repeat until config found or filesystem root reached

    Returns the path to the config file.
    Raises FileNotFoundError if no valid config is found.
    """
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    source = project_dir.resolve()

    while source != source.parent:
        # Priority 1: version-pioneer.toml (always valid if exists)
        vp_toml = source / "version-pioneer.toml"
        if vp_toml.exists():
            return vp_toml

        # Priority 2: pyproject.toml with [tool.version-pioneer] section
        pyproject_toml = source / "pyproject.toml"
        if pyproject_toml.exists():
            toml_dict = load_toml(pyproject_toml)
            # Only return if it has the [tool.version-pioneer] section
            if "tool" in toml_dict and "version-pioneer" in toml_dict["tool"]:
                return pyproject_toml
            # Otherwise, continue searching parent directories

        source = source.parent

    raise FileNotFoundError(
        "No version-pioneer.toml or pyproject.toml with [tool.version-pioneer] section "
        "found in any parent directory"
    )


def load_config(
    project_dir: str | PathLike | None = None,
) -> VersionPioneerConfigResult:
    """
    Load version-pioneer configuration from the appropriate config file.

    Priority:
    1. version-pioneer.toml (root level config, no section needed)
    2. pyproject.toml ([tool.version-pioneer] section)

    Returns a VersionPioneerConfigResult with normalized config.
    """
    config_file = find_config_file(project_dir)
    project_root = config_file.parent

    toml_dict = load_toml(config_file)

    if config_file.name == "version-pioneer.toml":
        # Root level config - use as-is
        return VersionPioneerConfigResult(
            config=toml_dict,
            config_file=config_file,
            project_root=project_root,
            source="version-pioneer.toml",
        )
    else:
        # pyproject.toml - extract from [tool.version-pioneer]
        vp_config = toml_dict.get("tool", {}).get("version-pioneer", {})
        return VersionPioneerConfigResult(
            config=vp_config,
            config_file=config_file,
            project_root=project_root,
            source="pyproject.toml",
        )


def get_config_value(
    config: dict[str, Any],
    key: str,
    *,
    default: Any = None,
    raise_error: bool = False,
    config_source: str = "config",
    return_path_object: bool = False,
) -> Any:
    """
    Get a value from the normalized config dict.

    Args:
        config: Normalized config dict (without tool.version-pioneer prefix)
        key: The key to get (e.g., "versionscript", "versionfile-sdist")
        default: Default value if key is missing
        raise_error: Raise KeyError if key is missing
        config_source: Description of config source for error messages
        return_path_object: Convert value to Path if found
    """
    if default is not None and raise_error:
        raise ValueError("default and raise_error cannot both be set.")

    if key not in config:
        if raise_error:
            raise KeyError(f"Missing key '{key}' in {config_source}")
        return default

    value = config[key]

    if return_path_object:
        return Path(value)
    return value


def normalize_pyproject_dict_to_config(
    pyproject_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract and return the normalized version-pioneer config from a pyproject.toml dict.

    This is useful when you already have the pyproject.toml dict loaded
    (e.g., from PDM context.config.data).
    """
    return pyproject_dict.get("tool", {}).get("version-pioneer", {})
