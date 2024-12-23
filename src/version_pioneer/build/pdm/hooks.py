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
        versionscript = Path(
            get_toml_value(
                context.config.data, ["tool", "version-pioneer", "versionscript"]
            )
        )
        version_dict = exec_version_py_to_get_version_dict(versionscript)

        # versionscript_code = versionscript.read_text()
        # version_module_globals = {}
        # exec(versionscript_code, version_module_globals)
        # version_dict = version_module_globals["get_version_dict"]()

        context.config.metadata["version"] = version_dict["version"]

        # Write the static version file
        if context.target != "editable":
            try:
                if context.target == "wheel":
                    versionfile = context.build_dir / Path(
                        get_toml_value(
                            context.config.data,
                            ["tool", "version-pioneer", "versionfile-wheel"],
                        )
                    )
                elif context.target == "sdist":
                    versionfile = context.build_dir / Path(
                        get_toml_value(
                            context.config.data,
                            ["tool", "version-pioneer", "versionfile-sdist"],
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
                    version_dict_to_str(version_dict, output_format="python")
                )
                # make it executable
                versionfile.chmod(versionfile.stat().st_mode | stat.S_IEXEC)
