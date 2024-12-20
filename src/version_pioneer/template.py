"""
This module should be able to be imported from anywhere without any dependencies, because it's used in setup.
"""

import textwrap

EXEC_OUTPUT_PYTHON = textwrap.dedent(
    """
    #!/usr/bin/env python3
    # GENERATED BY version-pioneer-{version_pioneer_version}
    # by evaluating the original _version.py file and storing the computed versions as a constant.

    def get_version_dict():
        return {version_dict}

    if __name__ == "__main__":
        import json

        print(json.dumps(get_version_dict()))
    """
).strip()


SETUP_PY = textwrap.dedent("""
    from setuptools import setup
    from version_pioneer.build.setuptools import get_version, get_cmdclass

    setup(
        version=get_version(),
        cmdclass=get_cmdclass(),
    )
""").strip()


INIT_PY = textwrap.dedent("""
    from ._version import get_version_dict

    __version__ = get_version_dict()["version"]
""").strip()


NO_VENDOR_VERSIONSCRIPT = textwrap.dedent("""
    from pathlib import Path

    from version_pioneer import get_version_dict_from_vcs, VersionPioneerConfig


    def get_version_dict():
        cfg = VersionPioneerConfig(
            style="pep440",
            tag_prefix="v",
            parentdir_prefix=None,
            verbose=False,
        )

        return get_version_dict_from_vcs(cfg, cwd=Path(__file__).parent)
""").strip()
