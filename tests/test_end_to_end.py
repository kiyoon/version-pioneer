import logging
import re
import subprocess
from pathlib import Path
from shutil import rmtree

import pytest

from .utils import run

logger = logging.getLogger(__name__)


def build_project(*args, check=True):
    if not args:
        args = ["-w"]

    return run("build", *args, check=check)


def test_build(new_hatchling_project: Path):
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

    whl = new_hatchling_project / "dist" / "my_app-0.1.0-py2.py3-none-any.whl"

    assert whl.exists()

    run("wheel", "unpack", whl)

    resolved_version_py = (
        new_hatchling_project / "my_app-0.1.0" / "my_app" / "_version.py"
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

    # There are unsaved changes in the project, so the second build will have a different version.
    ps = subprocess.run(
        ["git", "status"],
        cwd=new_hatchling_project,
        check=True,
        capture_output=True,
        text=True,
    )
    logger.info(ps.stdout)

    version_module_globals = {}
    version_module_code = (
        new_hatchling_project / "src" / "my_app" / "_version.py"
    ).read_text()
    exec(version_module_code, version_module_globals)
    version = version_module_globals["__version__"]

    logger.info(f"Version code: {version_module_code}")
    logger.info(f"Version: {version}")

    rmtree(new_hatchling_project / "dist")
    build_project()

    whls = list(
        (new_hatchling_project / "dist").glob(
            # "my_app-0.1.0+0.g*.dirty-py2.py3-none-any.whl"
            "*.whl"
        )
    )
    assert len(whls) == 1
    whl = whls[0]
    logger.info(f"Found wheel: {whl}")
    assert whl.exists()

    # metadata = email.parser.Parser().parsestr(
    #     (new_project / "my_app-1.0" / "my_app-1.0.dist-info" / "METADATA").read_text()
    # )
    #
    # assert "text/markdown" == metadata["Description-Content-Type"]
    # assert "# Level 1\n\nFancy *Markdown*.\n---\nFooter" == metadata.get_payload()


def test_invalid_config(new_hatchling_project):
    """
    Missing config makes the build fail with a meaningful error message.
    """
    pyp = new_hatchling_project / "pyproject.toml"

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
