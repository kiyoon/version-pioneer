"""
This module should be able to be imported from anywhere without any dependencies, because it's used in setup.
"""

import textwrap

EXEC_OUTPUT_PYTHON = textwrap.dedent(
    """
    #!/usr/bin/env python3
    # THIS "versionfile" IS GENERATED BY version-pioneer-{version_pioneer_version}
    # by evaluating the original versionscript and storing the computed versions as a constant.

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
    #!/usr/bin/env python3
    from pathlib import Path

    from version_pioneer.api import get_version_dict_wo_exec


    def get_version_dict():
        # NOTE: during installation, __file__ is not defined
        # When installed in editable mode, __file__ is defined
        # When installed in standard mode (when built), this file is replaced to a compiled versionfile.
        if "__file__" in globals():
            cwd = Path(__file__).parent
        else:
            cwd = Path.cwd()

        return get_version_dict_wo_exec(
            cwd=cwd,
            style="pep440",
            tag_prefix="v",
        )


    if __name__ == "__main__":
        import json

        print(json.dumps(get_version_dict()))
""").strip()
