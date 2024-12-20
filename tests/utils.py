from __future__ import annotations

import logging
import re
from pathlib import Path

from version_pioneer.utils.version_script import (
    exec_version_script,
    exec_version_script_code,
)

logger = logging.getLogger(__name__)


class VersionScriptResolutionError(Exception):
    pass


def verify_resolved_versionfile(resolved_versionscript_code: str):
    # does it have `def get_version_dict():`?
    if (
        re.search(
            r"^def get_version_dict\(.*\):$", resolved_versionscript_code, re.MULTILINE
        )
        is None
    ):
        raise VersionScriptResolutionError(
            f"Resolved _version.py code does not contain `def get_version_dict(): ...`: {resolved_versionscript_code}"
        )

    # Can you execute it without dependencies?
    version_dict = exec_version_script_code(resolved_versionscript_code)

    # Can you get the version?
    version = version_dict["version"]
    assert isinstance(version, str)

    # Does it have all keys in VersionDict TypedDict definition?
    # In TypedDict, __required_keys__, __optional_keys__ added in python 3.9
    # get_annotations() added in python 3.10
    # With lazy evaluation of ForwardRef, this is tricky.

    # for key, type_ in VersionDict.__annotations__.items():
    #     assert key in version_dict
    #     if isinstance(type_, ForwardRef):
    #         # https://stackoverflow.com/questions/76106117/python-resolve-forwardref
    #         # type_ = type_._evaluate(globals(), locals(), frozenset())  # Python 3.9+
    #         type_ = type_._evaluate(globals(), locals())
    #     assert isinstance(version_dict[key], type_)


def get_dynamic_version(project_dir: Path) -> str:
    version_module_code = project_dir / "src" / "my_app" / "_version.py"
    return exec_version_script(version_module_code)["version"]
