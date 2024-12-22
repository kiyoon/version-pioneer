import subprocess
from pathlib import Path
from shutil import rmtree

from tests.utils import assert_build_consistency, run, verify_resolved_version_py
from version_pioneer.api import get_version_py_code


def check_no_versionfile_build(cwd: Path):
    """
    Check when versionfile-build is not set. Must be used with xfail(raise=VersionPyResolutionError).
    """
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.1"], check=True)

    assert_build_consistency(version="0.1.1", cwd=cwd)

    # No need to build again. We check the _version.py file directly on sdist and wheel.
    Path(cwd / "dist-separated").rename(cwd / "dist")

    sdist = cwd / "dist" / "my_app-0.1.1.tar.gz"
    assert sdist.exists()
    subprocess.run(["tar", "xzf", sdist], cwd=cwd / "dist", check=True)
    unresolved_version_py = (
        cwd / "dist" / "my_app-0.1.1" / "src" / "my_app" / "_version.py"
    ).read_text()
    assert unresolved_version_py == get_version_py_code()
    verify_resolved_version_py(unresolved_version_py)  # expected to fail
    rmtree(cwd / "dist")

    # logger.info(list((cwd / "dist").glob("*")))
    whl = cwd / "dist" / "my_app-0.1.1-py3-none-any.whl"

    assert whl.exists()

    run("wheel", "unpack", whl, "--dest", cwd / "dist")

    unresolved_version_py = (
        cwd / "dist" / "my_app-0.1.1" / "my_app" / "_version.py"
    ).read_text()
    assert unresolved_version_py == get_version_py_code()
    verify_resolved_version_py(unresolved_version_py)  # expected to fail
