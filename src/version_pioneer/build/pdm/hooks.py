import stat
from pathlib import Path

from pdm.backend.hooks.base import Context

from version_pioneer.utils.exec_version_py import (
    exec_version_py_to_get_version_dict,
    version_dict_to_str,
)
from version_pioneer.utils.toml import get_toml_value


class VersionPioneerBuildHook:
    def pdm_build_initialize(self, context: Context):
        # Update metadata version
        versionscript_source = Path(
            get_toml_value(
                context.config.data, ["tool", "version-pioneer", "versionscript-source"]
            )
        )
        version_dict = exec_version_py_to_get_version_dict(versionscript_source)

        # versionscript_code = versionscript_source.read_text()
        # version_module_globals = {}
        # exec(versionscript_code, version_module_globals)
        # version_dict = version_module_globals["get_version_dict"]()

        context.config.metadata["version"] = version_dict["version"]

        # Write the static version file
        if context.target != "editable":
            try:
                if context.target == "wheel":
                    versionfile_build = context.build_dir / Path(
                        get_toml_value(
                            context.config.data,
                            ["tool", "version-pioneer", "versionfile-build"],
                        )
                    )
                elif context.target == "sdist":
                    versionfile_build = context.build_dir / Path(
                        get_toml_value(
                            context.config.data,
                            ["tool", "version-pioneer", "versionfile-source"],
                        )
                    )
                else:
                    raise ValueError(f"Unsupported target: {context.target}")
            except KeyError as e:
                print(str(e))  # Missing versionfile-source/build in pyproject.toml
                print("Skipping writing a constant version file")
            else:
                context.ensure_build_dir()
                versionfile_build.parent.mkdir(parents=True, exist_ok=True)
                versionfile_build.write_text(
                    version_dict_to_str(version_dict, output_format="python")
                )
                # make it executable
                versionfile_build.chmod(versionfile_build.stat().st_mode | stat.S_IEXEC)
