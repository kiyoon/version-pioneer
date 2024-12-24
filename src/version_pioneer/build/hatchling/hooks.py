from __future__ import annotations

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl
from hatchling.version.source.plugin.interface import VersionSourceInterface

from .build_hook import VersionPioneerBuildHook
from .version_source import VersionPioneerVersionSource


@hookimpl
def hatch_register_version_source() -> type[VersionSourceInterface]:
    return VersionPioneerVersionSource


@hookimpl
def hatch_register_build_hook() -> type[BuildHookInterface]:
    return VersionPioneerBuildHook
