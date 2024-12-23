from __future__ import annotations

from os import PathLike
from pathlib import Path

from .version_pioneer_core import VersionPioneerConfig
from .version_pioneer_core import __file__ as VERSION_PIONEER_CORE_FILE

VERSION_PIONEER_CORE_FILE = Path(VERSION_PIONEER_CORE_FILE).resolve()


def _version_pioneer_version():
    """
    Wrapper to avoid exposing the `get_version_dict` method which might confuse the users.
    """
    # NOTE: The _version.py is generated during the build process
    try:
        # If the package is installed as standard, the _version.py file is generated.
        from ._version import get_version_dict
    except ModuleNotFoundError:
        # If the package is installed as editable, the _version.py file doesn't exist.
        from .version_pioneer_core import get_version_dict

    return get_version_dict()["version"]


__version__ = _version_pioneer_version()


def get_version_dict_from_vcs(
    cfg: VersionPioneerConfig, cwd: str | PathLike | None = None
):
    """
    Get the version dictionary from the VCS.

    Override the method to use the current working directory by default, not the package __file__ directory.
    Because if used as non-vendored, the version is resolved from this Version-Pioneer package, not the package using it.

    It is still highly recommended to pass the package directory (cwd=Path(__file__).parent) to avoid any confusion.
    """
    from .version_pioneer_core import get_version_dict_from_vcs

    if cwd is None:
        cwd = Path.cwd()

    return get_version_dict_from_vcs(cfg, cwd=cwd)


# @lru_cache
# def pkg_is_editable():
#     direct_url = Distribution.from_name("version-pioneer").read_text("direct_url.json")
#     assert direct_url is not None
#     return json.loads(direct_url).get("dir_info", {}).get("editable", False)


# def get_version_py_path():
#     # If the package is installed as editable, the _version.py file is resolved and replaced.
#     # So we use another copy (copied during build) to print the original content.
#     if pkg_is_editable():
#         from version_pioneer._version import __file__ as VERSION_PY_FILE
#
#         return Path(VERSION_PY_FILE)
#     return Path(__file__).parent / "_version_orig.py"
