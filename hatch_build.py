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
        self.temp_version_file_original = None
        self.temp_version_file = None

        if version == "editable":
            return

        pyproject_toml = load_toml(Path(self.root) / "pyproject.toml")

        versionfile_source = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionfile-source"]
        )
        version_py = versionfile_source.read_text()

        version_orig_file = versionfile_source.with_name("_version_orig.py")
        if not (self.root / version_orig_file).exists():
            # Include original version file in the build, because it is needed in CLI or plugin
            # But this could be called twice (project_dir -> sdist -> wheel) so we need to check
            # if the file already exists
            self.temp_version_file_original = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode="w", delete=True
            )
            self.temp_version_file_original.write(version_py)
            self.temp_version_file_original.flush()
            build_data["force_include"][self.temp_version_file_original.name] = (
                version_orig_file
            )

        # evaluate the original _version.py file to get the computed version
        module_globals = {}
        exec(version_py, module_globals)

        # replace the file with the constant version
        self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
        self.temp_version_file.write(
            EXEC_OUTPUT_PYTHON.format(
                version_pioneer_version=module_globals["__version__"],
                version_dict=module_globals["__version_dict__"],
            )
        )
        self.temp_version_file.flush()

        # make it executable
        versionfile_build = Path(self.temp_version_file.name)
        versionfile_build.chmod(versionfile_build.stat().st_mode | stat.S_IEXEC)

        build_data["force_include"][self.temp_version_file.name] = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionfile-source"]
        )

    def finalize(
        self,
        version: str,
        build_data: dict[str, Any],
        artifact_path: str,
    ) -> None:
        # Delete the temporary version file
        if self.temp_version_file is not None:
            self.temp_version_file.close()

        if self.temp_version_file_original is not None:
            self.temp_version_file_original.close()
