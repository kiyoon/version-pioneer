import stat
from pathlib import Path

from pdm.backend.hooks.base import Context

from version_pioneer.api import exec_version_py


class VersionPioneerBuildHook:
    def pdm_build_initialize(self, context: Context):
        # Update metadata version
        versionfile_source = Path(
            context.config.data["tool"]["version-pioneer"]["versionfile-source"]
        )
        versionfile_code = versionfile_source.read_text()
        version_module_globals = {}
        exec(versionfile_code, version_module_globals)
        context.config.metadata["version"] = version_module_globals["__version__"]

        # Write the static version file
        if context.target != "editable":
            versionfile_build = context.build_dir / Path(
                context.config.data["tool"]["version-pioneer"]["versionfile-build"]
            )
            context.ensure_build_dir()
            versionfile_build.parent.mkdir(parents=True, exist_ok=True)
            versionfile_build.write_text(
                exec_version_py(versionfile_source, output_format="python")
            )
            # make it executable
            versionfile_build.chmod(versionfile_build.stat().st_mode | stat.S_IEXEC)
