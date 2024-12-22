from __future__ import annotations

import stat
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

from version_pioneer.api import exec_version_py
from version_pioneer.utils.toml import get_toml_value, load_toml


class VersionPioneerBuildHook(BuildHookInterface):
    PLUGIN_NAME = "version-pioneer"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        self.temp_version_file = None

        if version == "editable":
            return

        pyproject_toml = load_toml(Path(self.root) / "pyproject.toml")

        versionfile_source = Path(self.root) / get_toml_value(
            pyproject_toml, ["tool", "version-pioneer", "versionfile-source"]
        )

        # evaluate the original _version.py file to get the computed version
        # replace the file with the constant version
        try:
            versionfile_build = Path(
                pyproject_toml["tool"]["version-pioneer"]["versionfile-build"]
            )
        except KeyError:
            print("No versionfile-build specified in pyproject.toml")
            print("Skipping replacing the _version.py file")
        else:
            self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
            self.temp_version_file.write(
                exec_version_py(versionfile_source, output_format="python")
            )
            self.temp_version_file.flush()

            # make it executable
            versionfile_build_temp = Path(self.temp_version_file.name)
            versionfile_build_temp.chmod(
                versionfile_build_temp.stat().st_mode | stat.S_IEXEC
            )

            build_data["force_include"][self.temp_version_file.name] = versionfile_build

    def finalize(
        self,
        version: str,
        build_data: dict[str, Any],
        artifact_path: str,
    ) -> None:
        if self.temp_version_file is not None:
            # Delete the temporary version file
            self.temp_version_file.close()


@hookimpl
def hatch_register_build_hook() -> type[BuildHookInterface]:
    return VersionPioneerBuildHook
