# ruff: noqa: T201
from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from version_pioneer.api import exec_version_script_and_convert
from version_pioneer.utils.toml import (
    find_pyproject_toml,
    get_toml_value,
    load_toml,
)
from version_pioneer.utils.version_script import (
    convert_version_dict,
    exec_version_script,
    find_version_script_from_project_dir,
    find_version_script_from_pyproject_toml_dict,
)


def get_cmdclass(cmdclass: dict[str, Any] | None = None):
    """
    Get the custom setuptools subclasses used by Versioneer.

    If the package uses a different cmdclass (e.g. one from numpy), it
    should be provide as an argument.
    """
    if "versioneer" in sys.modules:
        del sys.modules["versioneer"]
        # this fixes the "python setup.py develop" case (also 'install' and
        # 'easy_install .'), in which subdependencies of the main project are
        # built (using setup.py bdist_egg) in the same python process. Assume
        # a main project A and a dependency B, which use different versions
        # of Versioneer. A's setup.py imports A's Versioneer, leaving it in
        # sys.modules by the time B's setup.py is executed, causing B to run
        # with the wrong versioneer. Setuptools wraps the sub-dep builds in a
        # sandbox that restores sys.modules to it's pre-build state, so the
        # parent is protected against the child's "import versioneer". By
        # removing ourselves from sys.modules here, before the child build
        # happens, we protect the child from the parent's versioneer too.
        # Also see https://github.com/python-versioneer/python-versioneer/issues/52

    cmds = {} if cmdclass is None else cmdclass.copy()

    # we add "version" to setuptools
    from setuptools import Command

    class CmdVersion(Command):
        description = "report generated version string"
        user_options: list[tuple[str, str, str]] = []  # noqa: RUF012
        boolean_options: list[str] = []  # noqa: RUF012

        def initialize_options(self) -> None:
            pass

        def finalize_options(self) -> None:
            pass

        def run(self) -> None:
            vers = exec_version_script(
                find_version_script_from_project_dir(
                    either_versionfile_or_versionscript=True
                )
            )
            print(f"Version: {vers['version']}")
            print(f" full-revisionid: {vers['full_revisionid']}")
            print(f" dirty: {vers['dirty']}")
            print(f" date: {vers['date']}")
            if vers["error"]:
                print(f" error: {vers['error']}")

    cmds["version"] = CmdVersion

    # we override "build_py" in setuptools
    #
    # most invocation pathways end up running build_py:
    #  distutils/build -> build_py
    #  distutils/install -> distutils/build ->..
    #  setuptools/bdist_wheel -> distutils/install ->..
    #  setuptools/bdist_egg -> distutils/install_lib -> build_py
    #  setuptools/install -> bdist_egg ->..
    #  setuptools/develop -> ?
    #  pip install:
    #   copies source tree to a tempdir before running egg_info/etc
    #   if .git isn't copied too, 'git describe' will fail
    #   then does setup.py bdist_wheel, or sometimes setup.py install
    #  setup.py egg_info -> ?

    # pip install -e . and setuptool/editable_wheel will invoke build_py
    # but the build_py command is not expected to copy any files.

    # we override different "build_py" commands for both environments
    if "build_py" in cmds:
        _build_py: Any = cmds["build_py"]
    else:
        from setuptools.command.build_py import build_py as _build_py

    class CmdBuildPy(_build_py):
        def run(self) -> None:
            _build_py.run(self)
            if getattr(self, "editable_mode", False):
                # During editable installs `.py` and data files are
                # not copied to build_lib
                return
            # now locate _version.py in the new build/ directory and replace
            # it with an updated value
            pyproject_toml_file = find_pyproject_toml()
            pyproject_toml = load_toml(pyproject_toml_file)
            versionfile_wheel: str | None = get_toml_value(
                pyproject_toml,
                ["tool", "version-pioneer", "versionfile-wheel"],
            )
            if versionfile_wheel is not None:
                versionscript = find_version_script_from_pyproject_toml_dict(
                    pyproject_toml, either_versionfile_or_versionscript=True
                )
                target_versionfile_content = exec_version_script_and_convert(
                    versionscript, output_format="python"
                )
                target_versionfile = Path(self.build_lib) / versionfile_wheel
                print(f"UPDATING {target_versionfile}")
                target_versionfile.write_text(target_versionfile_content)

    cmds["build_py"] = CmdBuildPy

    if "build_ext" in cmds:
        _build_ext: Any = cmds["build_ext"]
    else:
        from setuptools.command.build_ext import build_ext as _build_ext

    class CmdBuildExt(_build_ext):
        def run(self) -> None:
            _build_ext.run(self)
            if self.inplace:
                # build_ext --inplace will only build extensions in
                # build/lib<..> dir with no _version.py to write to.
                # As in place builds will already have a _version.py
                # in the module dir, we do not need to write one.
                return
            # now locate _version.py in the new build/ directory and replace
            # it with an updated value
            pyproject_toml_file = find_pyproject_toml()
            pyproject_toml = load_toml(pyproject_toml_file)
            versionfile_wheel: str | None = get_toml_value(
                pyproject_toml,
                ["tool", "version-pioneer", "versionfile-wheel"],
            )
            if versionfile_wheel is not None:
                versionscript = find_version_script_from_pyproject_toml_dict(
                    pyproject_toml, either_versionfile_or_versionscript=True
                )
                target_versionfile_content = exec_version_script_and_convert(
                    versionscript, output_format="python"
                )
                target_versionfile = Path(self.build_lib) / versionfile_wheel
                if not target_versionfile.exists():
                    print(
                        f"Warning: {target_versionfile} does not exist, skipping "
                        "version update. This can happen if you are running build_ext "
                        "without first running build_py."
                    )
                    return
                print(f"UPDATING {target_versionfile}")
                target_versionfile.write_text(target_versionfile_content)

    cmds["build_ext"] = CmdBuildExt

    def _run_directly_inside_source_tree(run_func: Callable):
        pyproject_toml_file = find_pyproject_toml()
        pyproject_toml = load_toml(pyproject_toml_file)
        versionscript: Path | None = get_toml_value(
            pyproject_toml,
            ["tool", "version-pioneer", "versionscript"],
            return_path_object=True,
        )
        if versionscript is None:
            raise ValueError("versionscript is not set in pyproject.toml")
        versionfile_sdist: Path | None = get_toml_value(
            pyproject_toml,
            ["tool", "version-pioneer", "versionfile-sdist"],
            return_path_object=True,
        )
        if versionfile_sdist is None:
            print("Skipping version update due to versionfile-sdist not set.")
            run_func()
            return

        versionscript = pyproject_toml_file.parent / versionscript
        versionfile_sdist = pyproject_toml_file.parent / versionfile_sdist

        if versionscript == versionfile_sdist:
            # HACK: replace _version.py directly in the source tree during build, and restore it.
            target_versionfile = versionscript
            print(f"UPDATING {target_versionfile}")
            target_versionfile_content = exec_version_script_and_convert(
                versionscript, output_format="python"
            )
            original_versionscript_content = versionscript.read_text()
            target_versionfile.write_text(target_versionfile_content)

            run_func()

            target_versionfile.write_text(original_versionscript_content)
        else:
            # HACK: write _version.py directly in the source tree during build.
            target_versionfile = versionfile_sdist
            target_versionfile_content = exec_version_script_and_convert(
                versionscript, output_format="python"
            )
            target_versionfile.write_text(target_versionfile_content)

            run_func()
            # We do not remove the versionfile-sdist. Put it as .gitignore.

    if "cx_Freeze" in sys.modules:  # cx_freeze enabled?
        try:
            from cx_Freeze.command.build_exe import (  # type: ignore
                BuildEXE as _build_exe,  # noqa: N813
            )
        except ImportError:  # cx_Freeze < 6.11
            from cx_Freeze.dist import build_exe as _build_exe  # type: ignore
        # nczeczulin reports that py2exe won't like the pep440-style string
        # as FILEVERSION, but it can be used for PRODUCTVERSION, e.g.
        # setup(console=[{
        #   "version": versioneer.get_version().split("+", 1)[0], # FILEVERSION
        #   "product_version": versioneer.get_version(),
        #   ...

        class CmdBuildEXE(_build_exe):
            def run(self) -> None:
                _run_directly_inside_source_tree(lambda: _build_exe.run(self))

        cmds["build_exe"] = CmdBuildEXE
        del cmds["build_py"]

    if "py2exe" in sys.modules:  # py2exe enabled?
        try:
            from py2exe.setuptools_buildexe import py2exe as _py2exe  # type: ignore
        except ImportError:
            from py2exe.distutils_buildexe import py2exe as _py2exe  # type: ignore

        class CmdPy2EXE(_py2exe):
            def run(self) -> None:
                _run_directly_inside_source_tree(lambda: _py2exe.run(self))

        cmds["py2exe"] = CmdPy2EXE

    # sdist farms its file list building out to egg_info
    if "egg_info" in cmds:
        _egg_info: Any = cmds["egg_info"]
    else:
        from setuptools.command.egg_info import egg_info as _egg_info

    class CmdEggInfo(_egg_info):
        def find_sources(self) -> None:
            # egg_info.find_sources builds the manifest list and writes it
            # in one shot
            super().find_sources()

            # Modify the filelist and normalize it
            # self.filelist.append("versioneer.py")

            pyproject_toml_file = find_pyproject_toml()
            pyproject_toml = load_toml(pyproject_toml_file)
            versionscript = find_version_script_from_pyproject_toml_dict(
                pyproject_toml, either_versionfile_or_versionscript=True
            )

            # There are rare cases where versionscript might not be
            # included by default, so we must be explicit
            self.filelist.append(str(versionscript))

            self.filelist.sort()
            self.filelist.remove_duplicates()

            # The write method is hidden in the manifest_maker instance that
            # generated the filelist and was thrown away
            # We will instead replicate their final normalization (to unicode,
            # and POSIX-style paths)
            from setuptools import unicode_utils

            normalized = [
                unicode_utils.filesys_decode(f).replace(os.sep, "/")
                for f in self.filelist.files
            ]

            manifest_filename = Path(self.egg_info) / "SOURCES.txt"
            manifest_filename.write_text("\n".join(normalized))

    cmds["egg_info"] = CmdEggInfo

    # we override different "sdist" commands for both environments
    if "sdist" in cmds:
        _sdist: Any = cmds["sdist"]
    else:
        from setuptools.command.sdist import sdist as _sdist

    class CmdSdist(_sdist):
        def run(self) -> None:
            pyproject_toml_file = find_pyproject_toml()
            pyproject_toml = load_toml(pyproject_toml_file)
            versionscript = find_version_script_from_pyproject_toml_dict(
                pyproject_toml, either_versionfile_or_versionscript=True
            )
            self.version_dict = exec_version_script(
                pyproject_toml_file.parent / versionscript
            )

            self.versionfile_sdist: Path | None = get_toml_value(
                pyproject_toml,
                ["tool", "version-pioneer", "versionfile-sdist"],
                return_path_object=True,
            )

            # unless we update this, the command will keep using the old
            # version
            self.distribution.metadata.version = self.version_dict["version"]
            return _sdist.run(self)

        def make_release_tree(self, base_dir: str, files: list[str]) -> None:
            _sdist.make_release_tree(self, base_dir, files)
            # now locate _version.py in the new base_dir directory
            # (remembering that it may be a hardlink) and replace it with an
            # updated value

            if self.versionfile_sdist is None:
                print("Skipping version update due to versionfile-sdist not set.")
            else:
                target_versionfile = Path(base_dir) / self.versionfile_sdist
                print(f"UPDATING {target_versionfile}")
                target_versionfile.write_text(
                    convert_version_dict(self.version_dict, output_format="python")
                )

    cmds["sdist"] = CmdSdist

    return cmds
