import logging
import re

import pytest

from .utils import append, run

logger = logging.getLogger(__name__)


def build_project(*args, check=True):
    if not args:
        args = ["-w"]

    return run("build", *args, check=check)


@pytest.mark.slow
def test_build(new_project):
    """
    Build a fake project end-to-end and verify wheel contents.
    """
    #     append(
    #         new_project / "pyproject.toml",
    #         """
    # [tool.hatch.build.hooks.version-pioneer]
    # """,
    #     )

    build_project()

    whl = new_project / "dist" / "my_app-0+unknown-py2.py3-none-any.whl"

    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_project / "my_app-0+unknown" / "my_app" / "_version.py"
    ).read_text()

    # does it have `__version_dict__ = { ... }`?
    assert (
        re.search(r"^__version_dict__ = \{.*\}$", resolved_version_py, re.MULTILINE)
        is not None
    )
    # and `__version__ = __version_dict__[...]`?
    assert (
        re.search(
            r"^__version__ = __version_dict__\[.*\]$", resolved_version_py, re.MULTILINE
        )
        is not None
    )

    # metadata = email.parser.Parser().parsestr(
    #     (new_project / "my_app-1.0" / "my_app-1.0.dist-info" / "METADATA").read_text()
    # )
    #
    # assert "text/markdown" == metadata["Description-Content-Type"]
    # assert "# Level 1\n\nFancy *Markdown*.\n---\nFooter" == metadata.get_payload()


@pytest.mark.slow
def test_invalid_config(new_project):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    pyp = new_project / "pyproject.toml"

    # If we leave out the config for good, the plugin doesn't get activated.
    pyp.write_text(pyp.read_text() + "[tool.hatch.build.hooks.version-pioneer]")

    out = build_project(check=False)

    # assert "hatch_fancy_pypi_readme.exceptions.ConfigurationError" in out, out
    # assert (
    #     "tool.hatch.metadata.hooks.fancy-pypi-readme.content-type is missing." in out
    # ), out
    # assert (
    #     "tool.hatch.metadata.hooks.fancy-pypi-readme.fragments is missing." in out
    # ), out
