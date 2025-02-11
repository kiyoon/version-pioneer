from hatchling.version.source.plugin.interface import VersionSourceInterface

from version_pioneer.utils.versionscript import (
    exec_versionscript,
    find_versionscript_from_project_dir,
)


class VersionPioneerVersionSource(VersionSourceInterface):
    PLUGIN_NAME = "version-pioneer"

    def get_version_data(self):
        versionscript = find_versionscript_from_project_dir(
            project_dir=self.root,
            either_versionfile_or_versionscript=True,
        )
        version_dict = exec_versionscript(versionscript)

        return {"version": version_dict["version"]}
