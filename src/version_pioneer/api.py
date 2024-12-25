from __future__ import annotations

import subprocess
import tempfile
import textwrap
from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from shutil import rmtree
from typing import Literal, overload

from version_pioneer.utils.files import (
    are_dir_trees_equal,
    find_root_dir_with_file,
    remove_files_recusively,
)
from version_pioneer.utils.version_script import (
    RESOLUTION_FORMAT_TYPE,
    ResolutionFormat,
    convert_version_dict,
)
from version_pioneer.version_pioneer_core import (
    VERSION_STYLE_TYPE,
    VersionPioneerConfig,
    VersionStyle,
    get_version_dict_from_vcs,
)


class VersionMismatchError(Exception):
    pass


def get_version_script_core_code():
    """Get the content of version_pioneer_core.py file."""
    from version_pioneer import VERSION_PIONEER_CORE_FILE, __version__

    version_py_code = VERSION_PIONEER_CORE_FILE.read_text()

    # Put header after the shebang line
    version_py_code = version_py_code.replace(
        "#!/usr/bin/env python3",
        textwrap.dedent(f"""
            #!/usr/bin/env python3
            # GENERATED BY version-pioneer-{__version__}
        """).strip(),
        1,
    )

    return version_py_code


def exec_version_script_and_convert(
    project_dir_or_version_script_file: str | PathLike | None = None,
    *,
    output_format: RESOLUTION_FORMAT_TYPE = ResolutionFormat.version_string,
):
    """
    Resolve the _version.py file for build, and return in python, string or json format.

    Examples:
        $ version-pioneer resolve-version --output-format=json
        {"version": "1.2.3", "full_revisionid": "xxxxxx", "dirty": False, "error": None, "date": "2024-12-17T12:25:42+0900"}

        $ version-pioneer resolve-version --output-format=python
        #!/usr/bin/env python3
        # GENERATED BY version-pioneer-v0.1.0
        def get_version_dict():
            return {"version": "0.3.2+15.g2127fd3.dirty", "full-revisionid": "2127fd373d14ed5ded497fc18ac1c1b667f93a7d", "dirty": True, "error": None, "date": "2024-12-17T12:25:42+0900"}

        if __name__ == "__main__":
            import json

            print(json.dumps(get_version_dict()))
    """  # noqa: E501
    from version_pioneer.utils.version_script import (
        exec_version_script,
        find_version_script_from_project_dir,
    )

    if project_dir_or_version_script_file is None:
        version_py_file = find_version_script_from_project_dir(
            Path.cwd(), either_versionfile_or_versionscript=True
        )
    else:
        project_dir_or_version_script_file = Path(project_dir_or_version_script_file)
        if project_dir_or_version_script_file.is_file():
            version_py_file = project_dir_or_version_script_file
        else:
            version_py_file = find_version_script_from_project_dir(
                project_dir_or_version_script_file,
                either_versionfile_or_versionscript=True,
            )

    version_dict = exec_version_script(version_py_file)
    return convert_version_dict(version_dict, output_format)


def get_version_dict_wo_exec(
    cwd: str | PathLike | None = None,
    *,
    style: VERSION_STYLE_TYPE = VersionStyle.pep440,
    tag_prefix: str = "v",
    parentdir_prefix: str | None = None,
):
    """
    WITHOUT using the installed _version.py file, get version with Version-Pioneer logic.

    Useful when you don't need to customise the _version.py file, and you work in non-Python projects
    so you don't care about re-evaluating the version file.

    Args:
        parentdir_prefix: The prefix of the parent directory. (e.g. {github_repo_name}-)
    """
    cfg = VersionPioneerConfig(
        style=VersionStyle(style),
        tag_prefix=tag_prefix,
        parentdir_prefix=parentdir_prefix,
    )

    version_dict = get_version_dict_from_vcs(
        cfg, cwd=Path.cwd() if cwd is None else cwd
    )
    return version_dict


def get_version_wo_exec_and_convert(
    cwd: str | PathLike | None = None,
    *,
    style: VERSION_STYLE_TYPE = VersionStyle.pep440,
    tag_prefix: str = "v",
    parentdir_prefix: str | None = None,
    output_format: RESOLUTION_FORMAT_TYPE = ResolutionFormat.version_string,
):
    """
    WITHOUT using the installed _version.py file, get version with Version-Pioneer logic, and return as a string.

    Useful when you don't need to customise the _version.py file, and you work in non-Python projects
    so you don't care about re-evaluating the version file.

    Args:
        project_dir: The root or child directory of the project.
        parentdir_prefix: The prefix of the parent directory. (e.g. {github_repo_name}-)
    """
    return convert_version_dict(
        get_version_dict_wo_exec(
            cwd=cwd,
            style=style,
            tag_prefix=tag_prefix,
            parentdir_prefix=parentdir_prefix,
        ),
        output_format,
    )


def _get_wheel_package_version(wheel_path: str | PathLike) -> str:
    # also works with sdist
    return Path(wheel_path).stem.split(".tar")[0].split("-")[1]


def _get_wheel_package_name_and_version(wheel_path: str | PathLike) -> str:
    split = Path(wheel_path).stem.split("-")
    return "-".join(split[:2])


# NOTE: if you name it with `test_`, it will be picked up by pytest by importing this module.
@overload
def build_consistency_test(
    project_dir: str | PathLike | None = None,
    *,
    delete_temp_dir: Literal[True],
    test_chaining: bool = True,
    expected_version: str | None = None,
    ignore_patterns: str | Sequence[str] = ("*.egg-info/SOURCES.txt"),
) -> None: ...


@overload
def build_consistency_test(
    project_dir: str | PathLike | None = None,
    *,
    delete_temp_dir: Literal[False],
    test_chaining: bool = True,
    expected_version: str | None = None,
    ignore_patterns: str | Sequence[str] = ("*.egg-info/SOURCES.txt"),
) -> Path: ...


@overload
def build_consistency_test(
    project_dir: str | PathLike | None = None,
    *,
    delete_temp_dir: bool = True,
    test_chaining: bool = True,
    expected_version: str | None = None,
    ignore_patterns: str | Sequence[str] = ("*.egg-info/SOURCES.txt"),
) -> Path | None: ...


def build_consistency_test(
    project_dir: str | PathLike | None = None,
    *,
    delete_temp_dir: bool = True,
    test_chaining: bool = True,
    expected_version: str | None = None,
    ignore_patterns: str | Sequence[str] = ("*.egg-info/SOURCES.txt"),
) -> Path | None:
    """
    Assure build equality with `build`, `build --wheel` and `build --sdist`,
    plus check chaining sdist builds (project -> sdist -> sdist).

    This is because (I assume) when building both wheel and sdist, it first generates sdist (which should include all
    files necessary for the wheel), then builds the wheel from the sdist. If you build with `build --wheel` only, it
    processes the files from the git project directory directly. Thus, it is likely that `build` (both) fails to include
    version from git describe, while `build --wheel` does.

    Also, the _version.py gets resolved twice, once for the sdist, and once for the wheel. This can result in different
    outputs, thus we need to check the equality.

    Note:
        - setuptools backend generates setup.cfg in the sdist, so *.egg-info/SOURCES.txt can be different.
        - Other backends may generate different files, so you may need to add more ignore patterns.
    """
    import verboselogs

    from version_pioneer.utils.build import build_project, unpack_wheel

    def _compare_tmp_dirs(dir1: Path, dir2: Path, *, error_msg: str):
        remove_files_recusively(dir1, patterns=ignore_patterns)
        remove_files_recusively(dir2, patterns=ignore_patterns)
        try:
            are_dir_trees_equal(
                dir1,
                dir2,
            )
        except FileNotFoundError as e:
            raise FileNotFoundError(error_msg) from e

    logger = verboselogs.VerboseLogger(__name__)

    ignore_patterns = (
        [ignore_patterns] if isinstance(ignore_patterns, str) else ignore_patterns
    )

    # Ensure command `uv` is available
    try:
        subprocess.run(["uv", "--version"], check=True)
    except FileNotFoundError:
        logger.error(
            "❌ Command `uv` is not available. Please install with `pip install uv` or `brew install uv`."
        )
        return None

    logger.info("Testing build consistency...")

    project_dir = Path.cwd() if project_dir is None else Path(project_dir)
    project_root = find_root_dir_with_file(project_dir, "pyproject.toml")

    # We don't need to change the cwd, as the build_project function does that.
    logger.info(f"Changing cwd to {project_root}")
    # os.chdir(project_root)

    # build the project
    temp_dir = Path(tempfile.mkdtemp())
    logger.info("Building the project with `uv build`")
    output, builds = build_project(
        "--out-dir", temp_dir / "dist-combined", cwd=project_root
    )

    assert len(builds) == 2, f"❌ Expected 2 builds. {output}"
    sdist_combined = builds[0]
    wheel_combined = builds[1]

    logger.info("Building the project with `uv build --sdist` and `uv build --wheel`")
    output, builds = build_project(
        "--sdist", "--out-dir", temp_dir / "dist", cwd=project_root
    )
    assert len(builds) == 1, f"❌ Expected 1 sdist to be built. {output}"
    sdist_separate = builds[0]

    output, builds = build_project(
        "--wheel", "--out-dir", temp_dir / "dist", cwd=project_root
    )
    assert len(builds) == 1, f"❌ Expected 1 wheel to be built. {output}"
    wheel_separate = builds[0]

    wheel_combined_version = _get_wheel_package_version(wheel_combined)
    wheel_separate_version = _get_wheel_package_version(wheel_separate)
    sdist_combined_version = _get_wheel_package_version(sdist_combined)
    sdist_separate_version = _get_wheel_package_version(sdist_separate)
    if expected_version is not None:
        assert (
            wheel_combined_version == expected_version
        ), f"❌ Expected version {expected_version}, but got {wheel_combined_version}"
    if not (
        wheel_combined_version
        == wheel_separate_version
        == sdist_combined_version
        == sdist_separate_version
    ):
        raise VersionMismatchError(
            f"❌ Versions are not consistent. {wheel_combined_version=}, {wheel_separate_version=}, "
            f"{sdist_combined_version=}, {sdist_separate_version=}",
            temp_dir,
        )

    if expected_version is None:
        expected_version = wheel_combined_version
        logger.info(f"Built version: {expected_version}")
    else:
        logger.info(f"✅ Built version: {expected_version}")

    unpack_wheel(wheel_combined, temp_dir / "dist-combined")
    unpack_wheel(wheel_separate, temp_dir / "dist")
    dir_name = _get_wheel_package_name_and_version(wheel_combined)

    _compare_tmp_dirs(
        temp_dir / "dist" / dir_name,
        temp_dir / "dist-combined" / dir_name,
        error_msg="❌ Wheel builds are not consistent.",
    )

    rmtree(temp_dir / "dist-combined" / dir_name)
    rmtree(temp_dir / "dist" / dir_name)

    logger.success("✅ 2 wheel builds are consistent.")

    subprocess.run(
        ["tar", "-xzf", sdist_separate, "--directory", temp_dir / "dist"], check=True
    )
    subprocess.run(
        ["tar", "-xzf", sdist_separate, "--directory", temp_dir / "dist-combined"],
        check=True,
    )

    _compare_tmp_dirs(
        temp_dir / "dist" / dir_name,
        temp_dir / "dist-combined" / dir_name,
        error_msg="❌ sdist builds are not consistent.",
    )

    rmtree(temp_dir / "dist-combined")
    # rmtree(temp_dir / "dist" / dir_name)

    logger.success("✅ 2 sdist builds are consistent.")

    if test_chaining:
        logger.info(
            "Building the project with `uv build --sdist` using the built sdist (chaining test)."
        )
        built_dir = temp_dir / "dist" / dir_name
        logger.info(f"Changing cwd to the built sdist directory: {built_dir}")
        # os.chdir(built_dir)

        # Ensure no git information is available
        ps = subprocess.run(
            ["git", "describe"],
            cwd=built_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        assert (
            ps.returncode == 128
        ), "❌ Your temp directory has a .git information. Not able to test properly..."

        output, builds = build_project(
            "--sdist", "--out-dir", temp_dir / "dist-chained", cwd=built_dir
        )
        assert len(builds) == 1, f"❌ Expected 1 sdist to be built. {output}"
        sdist_chained = builds[0]

        sdist_chained_version = _get_wheel_package_version(sdist_chained)
        if expected_version != sdist_chained_version:
            raise VersionMismatchError(
                f"❌ Versions are not consistent. {expected_version=}, {sdist_chained_version=}",
                temp_dir,
            )

        subprocess.run(
            ["tar", "-xzf", sdist_chained, "--directory", temp_dir / "dist-chained"],
            check=True,
        )
        # building may generate a build artifact like .pdm_build, so we reset the `built_dir`.
        rmtree(built_dir)
        subprocess.run(
            ["tar", "-xzf", sdist_separate, "--directory", temp_dir / "dist"],
            check=True,
        )
        built_dir = temp_dir / "dist" / dir_name

        _compare_tmp_dirs(
            built_dir,
            temp_dir / "dist-chained" / dir_name,
            error_msg="❌ Chained sdist builds are not consistent with the non-chained build."
            f"original={built_dir}  "
            f"chained={temp_dir / 'dist-chained' / dir_name}",
        )

        logger.success("✅ Chained sdist builds are consistent.")
        rmtree(temp_dir / "dist-chained")

        logger.info("Build wheel using the sdist.")
        output, builds = build_project(
            "--wheel", "--out-dir", temp_dir / "dist-chained", cwd=built_dir
        )
        assert len(builds) == 1, f"❌ Expected 1 wheel to be built. {output}"
        wheel_chained = builds[0]

        wheel_chained_version = _get_wheel_package_version(wheel_chained)
        if expected_version != wheel_chained_version:
            raise ChainingBuildVersionMismatchError(
                f"❌ Versions are not consistent. {expected_version=}, {wheel_chained_version=}",
                temp_dir,
            )

        rmtree(built_dir)
        unpack_wheel(wheel_separate, temp_dir / "dist")
        unpack_wheel(wheel_chained, temp_dir / "dist-chained")

        _compare_tmp_dirs(
            built_dir,
            temp_dir / "dist-chained" / dir_name,
            error_msg="❌ Chained wheel build is not consistent with the non-chained build."
            f"original={built_dir}  "
            f"chained={temp_dir / 'dist-chained' / dir_name}",
        )

        logger.success(
            "✅ sdist -> wheel chained build is consistent with the non-chained build."
        )

        logger.success(
            "💓 All tests passed! 3 sdist builds and 3 wheel builds are consistent."
        )
    else:
        logger.success(
            "💓 All tests passed! 2 sdist builds and 2 wheel builds are consistent."
        )

    if delete_temp_dir:
        logger.info(f"Deleting temporary directory {temp_dir}")
        rmtree(temp_dir)
        return None
    else:
        logger.info(f"Temporary directory is at {temp_dir}")
        return temp_dir
