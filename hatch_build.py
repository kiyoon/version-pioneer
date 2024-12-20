import sys
from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface

# Building version-pioneer using version-pioneer functions..
# without installing the package, we import the module.
# Make sure build-time dependencies are installed.
sys.path.append(str(Path(__file__).parent / "src"))

from version_pioneer.build.hatchling.build_hook import (
    VersionPioneerBuildHook,  # This hook will be used just by importing it.  # noqa: F401
)
from version_pioneer.utils.version_script import (
    exec_version_script,
    find_version_script_from_project_dir,
)


# We can't use VersionSource plugin as custom, so we use MetadataHook.
class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata: dict) -> None:
        """
        This updates the metadata mapping of the `project` table in-place.
        """
        # This also checks the valid config, so run it first.
        versionscript = find_version_script_from_project_dir(
            project_dir=self.root,
            either_versionfile_or_versionscript=True,
        )
        version_dict = exec_version_script(versionscript)
        metadata["version"] = version_dict["version"]
