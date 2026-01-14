# ruff: noqa: T201
from __future__ import annotations

import stat
from pathlib import Path

from pdm.backend.hooks.base import Context

from version_pioneer.utils.config import (
    get_config_value,
    normalize_pyproject_dict_to_config,
)
from version_pioneer.utils.versionscript import (
    convert_version_dict,
    exec_versionscript,
    find_versionscript_from_pyproject_toml_dict,
)


class VersionPioneerBuildHook:
    def pdm_build_initialize(self, context: Context):
        # Get normalized config
        config = normalize_pyproject_dict_to_config(context.config.data)

        # Update metadata version
        versionscript = find_versionscript_from_pyproject_toml_dict(
            context.config.data,
            project_root=context.root,
            either_versionfile_or_versionscript=True,
        )
        version_dict = exec_versionscript(context.root / versionscript)
        context.config.metadata["version"] = version_dict["version"]

        # Write the static version file
        if context.target != "editable":
            try:
                if context.target == "wheel":
                    versionfile = context.build_dir / Path(
                        get_config_value(
                            config,
                            "versionfile-wheel",
                            raise_error=True,
                            config_source="pyproject.toml",
                        )
                    )
                elif context.target == "sdist":
                    versionfile = context.build_dir / Path(
                        get_config_value(
                            config,
                            "versionfile-sdist",
                            raise_error=True,
                            config_source="pyproject.toml",
                        )
                    )
                else:
                    raise ValueError(f"Unsupported target: {context.target}")
            except KeyError as e:
                print(str(e))  # Missing versionfile-sdist/build in pyproject.toml
                print("Skipping writing a constant version file")
            else:
                context.ensure_build_dir()
                versionfile.parent.mkdir(parents=True, exist_ok=True)
                versionfile.write_text(
                    convert_version_dict(version_dict, output_format="python"),
                    encoding="utf-8",
                )
                # make it executable
                versionfile.chmod(versionfile.stat().st_mode | stat.S_IEXEC)
