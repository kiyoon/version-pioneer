# ruff: noqa: T201
from __future__ import annotations

import stat
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

from version_pioneer.utils.exec_version_py import (
    exec_version_py_code_to_get_version_dict,
    version_dict_to_str,
)
from version_pioneer.utils.toml import get_toml_value, load_toml


class VersionPioneerBuildHook(BuildHookInterface):
    PLUGIN_NAME = "version-pioneer"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """
        Args:
            version: editable, standard
        """
        self.temp_version_file = None

        if version == "editable":
            return

        pyproject_toml = load_toml(Path(self.root) / "pyproject.toml")

        versionfile_source = Path(
            get_toml_value(
                pyproject_toml, ["tool", "version-pioneer", "versionfile-source"]
            )
        )

        # evaluate the original _version.py file to get the computed version
        # replace the file with the constant version
        try:
            # In hatchling, versionfile-build setting doesn't actually get used.
            # Instead, the versionfile-source needs to be used to locate the build _version.py file.
            # We still check the existence of versionfile-build to see if users want to replace the _version.py file.
            versionfile_build = str(
                pyproject_toml["tool"]["version-pioneer"]["versionfile-build"]
            )
        except KeyError:
            print("No versionfile-build specified in pyproject.toml")
            print("Skipping replacing the _version.py file")
        else:
            # if versionfile_build != str(versionfile_source):
            #     raise ValueError(
            #         "For hatchling backend, versionfile-build must be the same as versionfile-source. "
            #         "Or set versionfile-build to None to skip replacing the _version.py file."
            #         f"Got {versionfile_build} and {versionfile_source}"
            #     )

            self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
            version_dict = exec_version_py_code_to_get_version_dict(
                versionfile_source.read_text()
            )
            self.temp_version_file.write(
                version_dict_to_str(version_dict, output_format="python")
            )
            self.temp_version_file.flush()

            # make it executable
            versionfile_build_temp = Path(self.temp_version_file.name)
            versionfile_build_temp.chmod(
                versionfile_build_temp.stat().st_mode | stat.S_IEXEC
            )

            build_data["force_include"][self.temp_version_file.name] = (
                versionfile_source
            )

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
