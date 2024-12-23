from __future__ import annotations

import stat
import sys
import tempfile
from os import PathLike
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

# import src/version_pioneer/template.py
sys.path.append(str(Path(__file__).parent / "src" / "version_pioneer"))
from template import EXEC_OUTPUT_PYTHON  # type: ignore


def load_toml(file: str | PathLike) -> dict[str, Any]:
    with open(file, "rb") as f:
        return tomllib.load(f)


class CustomPioneerBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        self.temp_version_file = None

        if version == "editable":
            return

        pyproject_toml = load_toml(Path(self.root) / "pyproject.toml")

        versionscript = Path(pyproject_toml["tool"]["version-pioneer"]["versionscript"])
        versionfile_sdist = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionfile-sdist"]
        )
        versionscript_code = versionscript.read_text()

        # evaluate the original _version.py file to get the computed version
        module_globals = {}
        exec(versionscript_code, module_globals)
        version_dict = module_globals["get_version_dict"]()

        # replace the file with the constant version
        self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
        self.temp_version_file.write(
            EXEC_OUTPUT_PYTHON.format(
                version_pioneer_version=version_dict["version"],
                version_dict=version_dict,
            )
        )
        self.temp_version_file.flush()

        # make it executable
        versionfile_wheel = Path(self.temp_version_file.name)
        versionfile_wheel.chmod(versionfile_wheel.stat().st_mode | stat.S_IEXEC)

        build_data["force_include"][self.temp_version_file.name] = versionfile_sdist

    def finalize(
        self,
        version: str,
        build_data: dict[str, Any],
        artifact_path: str,
    ) -> None:
        # Delete the temporary version file
        if self.temp_version_file is not None:
            self.temp_version_file.close()
