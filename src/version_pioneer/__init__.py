import json
from functools import lru_cache
from importlib.metadata import Distribution
from pathlib import Path

from ._version import __version__

# NOTE: _version_orig.py is generated during build
# Thus we import the correct file based on the installation mode.
# Other modules may import from here if you need _version.py content.
try:
    # you installed in editable (development) mode (pip install -e .)
    # this comes first (within try block) to ensure pyright type checker can recognise the symbols during development
    from ._version import (
        VersionDict,
        VersionPioneerConfig,
        VersionStyle,
        get_version_dict,
    )
except ImportError:
    # you installed in normal mode (pip install .)
    from ._version_orig import (
        VersionDict,
        VersionPioneerConfig,
        VersionStyle,
        get_version_dict,
    )


@lru_cache
def pkg_is_editable():
    direct_url = Distribution.from_name("version-pioneer").read_text("direct_url.json")
    assert direct_url is not None
    return json.loads(direct_url).get("dir_info", {}).get("editable", False)


@lru_cache
def get_version_py_path():
    # If the package is installed as editable, the _version.py file is resolved and replaced.
    # So we use another copy (copied during build) to print the original content.
    if pkg_is_editable():
        from version_pioneer._version import __file__ as VERSION_PY_FILE

        return Path(VERSION_PY_FILE)
    return Path(__file__).parent / "_version_orig.py"
