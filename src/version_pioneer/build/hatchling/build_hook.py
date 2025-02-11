# ruff: noqa: T201
from __future__ import annotations

import stat
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from version_pioneer.utils.toml import get_toml_value, load_toml
from version_pioneer.utils.versionscript import (
    convert_version_dict,
    exec_versionscript,
    find_versionscript_from_project_dir,
)


class VersionPioneerBuildHook(BuildHookInterface):
    PLUGIN_NAME = "version-pioneer"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """
        Execute either versionscript or versionfile-sdist and write to versionfile-sdist.

        Note:
            versionfile-wheel is not used for hatchling.

        Args:
            version: editable, standard (note there's no separation from sdist and wheel)
        """
        self.temp_versionfile = None

        if version == "editable":
            return

        pyproject_toml = load_toml(Path(self.root) / "pyproject.toml")

        # This also checks the valid config, so run it first.
        versionscript = find_versionscript_from_project_dir(
            project_dir=self.root,
            either_versionfile_or_versionscript=True,
        )

        # In hatchling, versionfile-wheel setting doesn't get used.
        # Instead, the versionfile-sdist needs to be used to locate the build _version.py file.
        versionfile_sdist: Path | None = get_toml_value(
            pyproject_toml,
            ["tool", "version-pioneer", "versionfile-sdist"],
            return_path_object=True,
        )
        if versionfile_sdist is None:
            print("No versionfile-sdist specified in pyproject.toml")
            print("Skipping writing a constant version file")
            return
        else:
            # NOTE: Setting delete=True will delete too early on Windows
            self.temp_versionfile = tempfile.NamedTemporaryFile(mode="w", delete=False)  # noqa: SIM115
            version_dict = exec_versionscript(versionscript)
            self.temp_versionfile.write(
                convert_version_dict(version_dict, output_format="python")
            )
            self.temp_versionfile.flush()

            # make it executable
            versionfile_build_temp = Path(self.temp_versionfile.name)
            versionfile_build_temp.chmod(
                versionfile_build_temp.stat().st_mode | stat.S_IEXEC
            )

            build_data["force_include"][self.temp_versionfile.name] = versionfile_sdist

    def finalize(
        self,
        version: str,
        build_data: dict[str, Any],
        artifact_path: str,
    ) -> None:
        if self.temp_versionfile is not None:
            # Delete the temporary version file
            self.temp_versionfile.close()
            Path(self.temp_versionfile.name).unlink()
