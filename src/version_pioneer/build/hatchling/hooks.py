# ruff: noqa: T201
from __future__ import annotations

import stat
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

from version_pioneer.utils.exec_version_script import (
    exec_version_script,
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

        versionscript = Path(
            get_toml_value(pyproject_toml, ["tool", "version-pioneer", "versionscript"])
        )

        # evaluate the original _version.py file to get the computed version
        # replace the file with the constant version
        try:
            # In hatchling, versionfile-wheel setting doesn't get used.
            # Instead, the versionfile-sdist needs to be used to locate the build _version.py file.
            versionfile_sdist = Path(
                get_toml_value(
                    pyproject_toml, ["tool", "version-pioneer", "versionfile-sdist"]
                )
            )
        except KeyError:
            print("No versionfile-sdist specified in pyproject.toml")
            print("Skipping writing a constant version file")
        else:
            # if versionfile_wheel != str(versionfile_sdist):
            #     raise ValueError(
            #         "For hatchling backend, versionfile-wheel must be the same as versionfile-sdist. "
            #         "Or set versionfile-wheel to None to skip replacing the _version.py file."
            #         f"Got {versionfile_wheel} and {versionfile_sdist}"
            #     )

            self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
            version_dict = exec_version_script(versionscript.read_text())
            self.temp_version_file.write(
                version_dict_to_str(version_dict, output_format="python")
            )
            self.temp_version_file.flush()

            # make it executable
            versionfile_build_temp = Path(self.temp_version_file.name)
            versionfile_build_temp.chmod(
                versionfile_build_temp.stat().st_mode | stat.S_IEXEC
            )

            build_data["force_include"][self.temp_version_file.name] = versionfile_sdist

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
