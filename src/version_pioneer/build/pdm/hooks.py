# ruff: noqa: T201
from __future__ import annotations

import stat
from pathlib import Path

from pdm.backend.hooks.base import Context

from version_pioneer.utils.toml import get_toml_value
from version_pioneer.utils.version_script import (
    convert_version_dict,
    exec_version_script,
    find_version_script_from_pyproject_toml_dict,
)


class VersionPioneerBuildHook:
    def pdm_build_initialize(self, context: Context):
        # Update metadata version
        versionscript = find_version_script_from_pyproject_toml_dict(
            context.config.data, either_versionfile_or_versionscript=True
        )
        version_dict = exec_version_script(versionscript)
        context.config.metadata["version"] = version_dict["version"]

        # Write the static version file
        if context.target != "editable":
            try:
                if context.target == "wheel":
                    versionfile = context.build_dir / Path(
                        get_toml_value(
                            context.config.data,
                            ["tool", "version-pioneer", "versionfile-wheel"],
                            raise_error=True,
                        )
                    )
                elif context.target == "sdist":
                    versionfile = context.build_dir / Path(
                        get_toml_value(
                            context.config.data,
                            ["tool", "version-pioneer", "versionfile-sdist"],
                            raise_error=True,
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
                    convert_version_dict(version_dict, output_format="python")
                )
                # make it executable
                versionfile.chmod(versionfile.stat().st_mode | stat.S_IEXEC)
