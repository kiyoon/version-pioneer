#!/usr/bin/env python3
"""
Generate a version number from Git tags (e.g. tag "v1.2.3" and 4 commits -> "1.2.3+4.g123abcdef").

It will be replaced with a much shorter file in distribution tarballs (built by `uv build`, `pyproject-build`)
that just contains two constants: `__version_dict__` and `__version__`.

Refactored from Versioneer's _version.py (for git).

Note:
    - Should be compatible with python 3.8+ without any dependencies.
    - This file is usually located at `src/my_package/_version.py`.
    - `src/my_package/__init__.py` should import `__version__` from this file.
    - It should also be able to be run as a script to print the version number.
    - Some may want to `exec` this file and get __version__ from the globals. This is how hatch determines the version.
        - Using `from __future__ import ...` with dataclasses makes it hard to `exec` this file, so you MUST NOT use both here.
            - See https://github.com/mkdocs/mkdocs/issues/3141
              https://github.com/pypa/hatch/issues/1863
              https://github.com/sqlalchemy/alembic/issues/1419
            - For now, we don't future import. In dataclass definition, we use `typing.Optional` instead of `| None`
              until we drop support for Python 3.9.
"""

# ruff: noqa: T201 FA100

import errno
import functools
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Optional, TypedDict


class VersionStyle(str, Enum):
    pep440 = "pep440"
    pep440_branch = "pep440_branch"
    pep440_pre = "pep440_pre"
    pep440_post = "pep440_post"
    pep440_post_branch = "pep440_post_branch"
    git_describe = "git_describe"
    git_describe_long = "git_describe_long"
    digits = "digits"


# ┌──────────────────────────────────────────┐
# │     Modify the configuration below.      │
# └──────────────────────────────────────────┘
@dataclass(frozen=True)
class VersionPioneerConfig:
    style: VersionStyle = VersionStyle.pep440
    tag_prefix: str = "v"
    # if there is no .git, like it's a source tarball downloaded from GitHub Releases,
    # find version from the name of the parent directory.
    # e.g. setting it to "github-repo-name-" will find the version from "github-repo-name-1.2.3"
    parentdir_prefix: Optional[str] = None
    verbose: bool = False


class VersionDict(TypedDict):
    """Type of __version_dict__."""

    version: "str | None"
    full_revisionid: "str | None"
    dirty: "bool | None"
    error: "str | None"
    date: "str | None"


try:
    _CURRENT_DIR = Path(__file__).resolve().parent
except NameError:
    # NOTE: py2exe/bbfreeze/non-cpython implementations may not have __file__.
    _CURRENT_DIR = Path.cwd()


class NotThisMethodError(Exception):
    """Exception raised if a method is not valid for the current scenario."""


@dataclass(frozen=True)
class GitPieces:
    """
    Get version from 'git describe' in the root of the source tree.

    This only gets called if the git-archive 'subst' keywords were *not*
    expanded, and _version.py hasn't already been rewritten with a short
    version string, meaning we're inside a checked out source tree.
    """

    long: str
    short: str
    branch: str
    closest_tag: Optional[str]
    distance: int
    dirty: bool
    error: Optional[str]
    date: Optional[str] = None

    @classmethod
    def from_vcs(
        cls: "type[GitPieces]",
        tag_prefix: str,
        root: "str | PathLike",
        *,
        verbose: bool = False,
    ) -> "GitPieces":
        if sys.platform == "win32":
            git_commands = ["git.cmd", "git.exe"]
        else:
            git_commands = ["git"]

        # GIT_DIR can interfere with correct operation of Versioneer.
        # It may be intended to be passed to the Versioneer-versioned project,
        # but that should not change where we get our version from.
        env = os.environ.copy()
        env.pop("GIT_DIR", None)
        runner = functools.partial(_run_command, env=env, verbose=verbose)

        _, rc = runner(
            git_commands, ["rev-parse", "--git-dir"], cwd=root, hide_stderr=not verbose
        )
        if rc != 0:
            if verbose:
                print(f"Directory {root} not under git control")
            raise NotThisMethodError("'git rev-parse --git-dir' returned error")

        # if there is a tag matching tag_prefix, this yields TAG-NUM-gHEX[-dirty]
        # if there isn't one, this yields HEX[-dirty] (no NUM)
        describe_out, rc = runner(
            git_commands,
            [
                "describe",
                "--tags",
                "--dirty",
                "--always",
                "--long",
                "--match",
                f"{tag_prefix}[[:digit:]]*",
            ],
            cwd=root,
        )
        # --long was added in git-1.5.5
        if describe_out is None:
            raise NotThisMethodError("'git describe' failed")
        describe_out = describe_out.strip()
        full_out, rc = runner(git_commands, ["rev-parse", "HEAD"], cwd=root)
        if full_out is None:
            raise NotThisMethodError("'git rev-parse' failed")
        full_out = full_out.strip()

        pieces: dict[str, Any] = {}
        pieces["long"] = full_out
        pieces["short"] = full_out[:7]  # maybe improved later
        pieces["error"] = None

        branch_name, rc = runner(
            git_commands, ["rev-parse", "--abbrev-ref", "HEAD"], cwd=root
        )
        # --abbrev-ref was added in git-1.6.3
        if rc != 0 or branch_name is None:
            raise NotThisMethodError("'git rev-parse --abbrev-ref' returned error")
        branch_name = branch_name.strip()

        if branch_name == "HEAD":
            # If we aren't exactly on a branch, pick a branch which represents
            # the current commit. If all else fails, we are on a branchless
            # commit.
            branches, rc = runner(git_commands, ["branch", "--contains"], cwd=root)
            # --contains was added in git-1.5.4
            if rc != 0 or branches is None:
                raise NotThisMethodError("'git branch --contains' returned error")
            branches = branches.split("\n")

            # Remove the first line if we're running detached
            if "(" in branches[0]:
                branches.pop(0)

            # Strip off the leading "* " from the list of branches.
            branches = [branch[2:] for branch in branches]
            if "master" in branches:
                branch_name = "master"
            elif not branches:
                branch_name = None
            else:
                # Pick the first branch that is returned. Good or bad.
                branch_name = branches[0]

        pieces["branch"] = branch_name

        # parse describe_out. It will be like TAG-NUM-gHEX[-dirty] or HEX[-dirty]
        # TAG might have hyphens.
        git_describe = describe_out

        # look for -dirty suffix
        dirty = git_describe.endswith("-dirty")
        pieces["dirty"] = dirty
        if dirty:
            git_describe = git_describe[: git_describe.rindex("-dirty")]

        # now we have TAG-NUM-gHEX or HEX

        if "-" in git_describe:
            # TAG-NUM-gHEX
            mo = re.search(r"^(.+)-(\d+)-g([0-9a-f]+)$", git_describe)
            if not mo:
                # unparsable. Maybe git-describe is misbehaving?
                pieces["error"] = (
                    f"unable to parse git-describe output: '{describe_out}'"
                )
                return cls(**pieces)

            # tag
            full_tag = mo.group(1)
            if not full_tag.startswith(tag_prefix):
                if verbose:
                    print(f"tag '{full_tag}' doesn't start with prefix '{tag_prefix}'")
                pieces["error"] = (
                    f"tag '{full_tag}' doesn't start with prefix '{tag_prefix}'"
                )
                return cls(**pieces)
            pieces["closest_tag"] = full_tag[len(tag_prefix) :]

            # distance: number of commits since tag
            pieces["distance"] = int(mo.group(2))

            # commit: short hex revision ID
            pieces["short"] = mo.group(3)

        else:
            # HEX: no tags
            pieces["closest_tag"] = None
            out, rc = runner(
                git_commands, ["rev-list", "HEAD", "--left-right"], cwd=root
            )
            assert out is not None
            pieces["distance"] = len(out.split())  # total number of commits

        # commit date: see ISO-8601 comment in git_versions_from_keywords()
        out, rc = runner(git_commands, ["show", "-s", "--format=%ci", "HEAD"], cwd=root)
        assert out is not None
        date = out.strip()
        # Use only the last line.  Previous lines may contain GPG signature
        # information.
        date = date.splitlines()[-1]
        pieces["date"] = date.strip().replace(" ", "T", 1).replace(" ", "", 1)

        return cls(**pieces)

    @property
    def _plus_or_dot(self) -> str:
        """Return a + if we don't already have one, else return a ."""
        if self.closest_tag is None:
            return "+"
        elif "+" in self.closest_tag:
            return "."
        return "+"

    def _render_pep440(self) -> str:
        """
        Build up version string, with post-release "local version identifier".

        Our goal: TAG[+DISTANCE.gHEX[.dirty]] . Note that if you
        get a tagged build and then dirty it, you'll get TAG+0.gHEX.dirty

        Exceptions:
        1: no tags. git_describe was just HEX. 0+untagged.DISTANCE.gHEX[.dirty]
        """
        if self.closest_tag:
            rendered = self.closest_tag
            if self.distance or self.dirty:
                rendered += self._plus_or_dot
                rendered += f"{self.distance}.g{self.short}"
                if self.dirty:
                    rendered += ".dirty"
        else:
            # exception #1
            rendered = f"0+untagged.{self.distance}.g{self.short}"
            if self.dirty:
                rendered += ".dirty"
        return rendered

    def _render_pep440_branch(self) -> str:
        """
        TAG[[.dev0]+DISTANCE.gHEX[.dirty]] .

        The ".dev0" means not master branch. Note that .dev0 sorts backwards
        (a feature branch will appear "older" than the master branch).

        Exceptions:
        1: no tags. 0[.dev0]+untagged.DISTANCE.gHEX[.dirty]
        """
        if self.closest_tag:
            rendered = self.closest_tag
            if self.distance or self.dirty:
                if self.branch != "master":
                    rendered += ".dev0"
                rendered += self._plus_or_dot
                rendered += f"{self.distance}.g{self.short}"
                if self.dirty:
                    rendered += ".dirty"
        else:
            # exception #1
            rendered = "0"
            if self.branch != "master":
                rendered += ".dev0"
            rendered += f"+untagged.{self.distance}.g{self.short}"
            if self.dirty:
                rendered += ".dirty"
        return rendered

    @staticmethod
    def _pep440_split_post(ver: str) -> "tuple[str, int | None]":
        """
        Split pep440 version string at the post-release segment.

        Returns the release segments before the post-release and the
        post-release version number (or -1 if no post-release segment is present).
        """
        vc = str.split(ver, ".post")
        return vc[0], int(vc[1] or 0) if len(vc) == 2 else None

    def _render_pep440_pre(self) -> str:
        """
        TAG[.postN.devDISTANCE] -- No -dirty.

        Exceptions:
        1: no tags. 0.post0.devDISTANCE
        """
        if self.closest_tag:
            if self.distance:
                # update the post release segment
                tag_version, post_version = self._pep440_split_post(self.closest_tag)
                rendered = tag_version
                if post_version is not None:
                    rendered += f".post{post_version}.dev{self.distance}"
                else:
                    rendered += f".post0.dev{self.distance}"
            else:
                # no commits, use the tag as the version
                rendered = self.closest_tag
        else:
            # exception #1
            rendered = f"0.post0.dev{self.distance}"
        return rendered

    def _render_pep440_post(self) -> str:
        """
        TAG[.postDISTANCE[.dev0]+gHEX] .

        The ".dev0" means dirty. Note that .dev0 sorts backwards
        (a dirty tree will appear "older" than the corresponding clean one),
        but you shouldn't be releasing software with -dirty anyways.

        Exceptions:
        1: no tags. 0.postDISTANCE[.dev0]
        """
        if self.closest_tag:
            rendered = self.closest_tag
            if self.distance or self.dirty:
                rendered += f".post{self.distance}"
                if self.dirty:
                    rendered += ".dev0"
                rendered += self._plus_or_dot
                rendered += f"g{self.short}"
        else:
            # exception #1
            rendered = f"0.post{self.distance}"
            if self.dirty:
                rendered += ".dev0"
            rendered += f"+g{self.short}"
        return rendered

    def _render_pep440_post_branch(self) -> str:
        """
        TAG[.postDISTANCE[.dev0]+gHEX[.dirty]] .

        The ".dev0" means not master branch.

        Exceptions:
        1: no tags. 0.postDISTANCE[.dev0]+gHEX[.dirty]
        """
        if self.closest_tag:
            rendered = self.closest_tag
            if self.distance or self.dirty:
                rendered += f".post{self.distance}"
                if self.branch != "master":
                    rendered += ".dev0"
                rendered += self._plus_or_dot
                rendered += f"g{self.short}"
                if self.dirty:
                    rendered += ".dirty"
        else:
            # exception #1
            rendered = f"0.post{self.distance}"
            if self.branch != "master":
                rendered += ".dev0"
            rendered += f"+g{self.short}"
            if self.dirty:
                rendered += ".dirty"
        return rendered

    def _render_git_describe(self) -> str:
        """
        TAG[-DISTANCE-gHEX][-dirty].

        Like 'git describe --tags --dirty --always'.

        Exceptions:
        1: no tags. HEX[-dirty]  (note: no 'g' prefix)
        """
        if self.closest_tag:
            rendered = self.closest_tag
            if self.distance:
                rendered += f"-{self.distance}-g{self.short}"
        else:
            # exception #1
            rendered = self.short
        if self.dirty:
            rendered += "-dirty"
        return rendered

    def _render_git_describe_long(self) -> str:
        """
        TAG-DISTANCE-gHEX[-dirty].

        Like 'git describe --tags --dirty --always -long'.
        The distance/hash is unconditional.

        Exceptions:
        1: no tags. HEX[-dirty]  (note: no 'g' prefix)
        """
        if self.closest_tag:
            rendered = self.closest_tag
            rendered += f"-{self.distance}-g{self.short}"
        else:
            # exception #1
            rendered = self.short
        if self.dirty:
            rendered += "-dirty"
        return rendered

    def _render_digits(self) -> str:
        """
        TAG.DISTANCE.

        For example, 'v1.2.3+4.g1abcdef' -> '1.2.3.4' and
        'v1.2.3+4.g1abcdef.dirty' -> '1.2.3.5' (dirty counts as 1 commit further).

        Digit-only version string that is compatible with most package managers.

        Note:
            - New in Version-Pioneer.
            - Compatible with Chrome extension version format.
                - Chrome extension version should not have more than 4 segments, so make sure the tags are up to 3 segments.
        """
        if self.error:
            raise ValueError("Unable to render version")

        if self.closest_tag:
            closest_tag: str = self.closest_tag
        else:
            closest_tag = "0"

        version = closest_tag
        if self.distance or self.dirty:
            if self.dirty:
                version += f".{self.distance + 1}"
            else:
                version += f".{self.distance}"

        return version

    def render(self, style: VersionStyle = VersionStyle.pep440) -> VersionDict:
        """Render the given version pieces into the requested style."""
        if self.error:
            return {
                "version": "unknown",
                "full_revisionid": self.long,
                "dirty": None,
                "error": self.error,
                "date": None,
            }

        if style == "pep440":
            rendered = self._render_pep440()
        elif style == "pep440_branch":
            rendered = self._render_pep440_branch()
        elif style == "pep440_pre":
            rendered = self._render_pep440_pre()
        elif style == "pep440_post":
            rendered = self._render_pep440_post()
        elif style == "pep440_post_branch":
            rendered = self._render_pep440_post_branch()
        elif style == "git_describe":
            rendered = self._render_git_describe()
        elif style == "git_describe_long":
            rendered = self._render_git_describe_long()
        elif style == "digits":
            rendered = self._render_digits()
        else:
            raise ValueError(f"unknown style '{style}'")

        return {
            "version": rendered,
            "full_revisionid": self.long,
            "dirty": self.dirty,
            "error": None,
            "date": self.date,
        }


def _get_keywords() -> "dict[str, str]":
    """Get the keywords needed to look up the version information."""
    # these strings will be replaced by git during git-archive.
    # setup.py/versioneer.py will grep for the variable names, so they must
    # each be defined on a line of their own. _version.py will just call
    # get_keywords().
    git_refnames = "$Format:%d$"
    git_full = "$Format:%H$"
    git_date = "$Format:%ci$"
    keywords = {"refnames": git_refnames, "full": git_full, "date": git_date}
    return keywords


def _run_command(
    commands: "list[str]",
    args: "list[str | PathLike]",
    *,
    cwd: "str | PathLike | None" = None,
    hide_stderr: bool = False,
    env: "dict[str, str] | None" = None,
    verbose: bool = False,
) -> "tuple[str | None, int | None]":
    """Call the given command(s)."""
    assert isinstance(commands, list)
    process = None

    popen_kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        # This hides the console window if pythonw.exe is used
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        popen_kwargs["startupinfo"] = startupinfo

    for command in commands:
        dispcmd = str([command, *args])
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            process = subprocess.Popen(
                [command, *args],
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=(subprocess.PIPE if hide_stderr else None),
                **popen_kwargs,
            )
            break
        except OSError as e:
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print(f"unable to run {dispcmd}")
                print(e)
            return None, None
    else:
        if verbose:
            print(f"unable to find command, tried {commands}")
        return None, None
    stdout = process.communicate()[0].strip().decode()
    if process.returncode != 0:
        if verbose:
            print(f"unable to run {dispcmd} (error)")
            print(f"stdout was {stdout}")
        return None, process.returncode
    return stdout, process.returncode


def _git_versions_from_keywords(
    keywords: "dict[str, str]",
    tag_prefix: str,
    *,
    verbose: bool = False,
) -> VersionDict:
    """Get version information from git keywords."""
    if "refnames" not in keywords:
        raise NotThisMethodError("Short version file found")
    date = keywords.get("date")
    if date is not None:
        # Use only the last line.  Previous lines may contain GPG signature
        # information.
        date = date.splitlines()[-1]

        # git-2.2.0 added "%cI", which expands to an ISO-8601 -compliant
        # datestamp. However we prefer "%ci" (which expands to an "ISO-8601
        # -like" string, which we must then edit to make compliant), because
        # it's been around since git-1.5.3, and it's too difficult to
        # discover which version we're using, or to work around using an
        # older one.
        date = date.strip().replace(" ", "T", 1).replace(" ", "", 1)
    refnames = keywords["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("keywords are unexpanded, not using")
        raise NotThisMethodError("unexpanded keywords, not a git-archive tarball")
    refs = {r.strip() for r in refnames.strip("()").split(",")}
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    tag_prefix = "tag: "
    tags = {r[len(tag_prefix) :] for r in refs if r.startswith(tag_prefix)}
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = {r for r in refs if re.search(r"\d", r)}
        if verbose:
            print("discarding '{}', no digits".format(",".join(refs - tags)))
    if verbose:
        print("likely tags: {}".format(",".join(sorted(tags))))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix) :]
            # Filter out refs that exactly match prefix or that don't start
            # with a number once the prefix is stripped (mostly a concern
            # when prefix is '')
            if not re.match(r"\d", r):
                continue
            if verbose:
                print(f"picking {r}")
            return {
                "version": r,
                "full_revisionid": keywords["full"].strip(),
                "dirty": False,
                "error": None,
                "date": date,
            }
    # no suitable tags, so version is "0+unknown", but full hex is still there
    if verbose:
        print("no suitable tags, using unknown + full revision id")
    return {
        "version": "0+unknown",
        "full_revisionid": keywords["full"].strip(),
        "dirty": False,
        "error": "no suitable tags",
        "date": None,
    }


def _find_root_dir_with_file(
    source: "str | PathLike", marker: "str | Iterable[str]"
) -> Path:
    """
    Find the first parent directory containing a specific "marker", relative to a file path.
    """
    source = Path(source).resolve()
    if isinstance(marker, str):
        marker = {marker}

    while source != source.parent:
        if any((source / m).exists() for m in marker):
            return source

        source = source.parent

    raise FileNotFoundError(f"File {marker} not found in any parent directory")


def _versions_from_parentdir(
    parentdir_prefix: str, root: "str | PathLike", *, verbose: bool = False
) -> VersionDict:
    """
    Try to determine the version from the parent directory name.

    Source tarballs conventionally unpack into a directory that includes both the project name and a version string.
    """
    rootdirs = []

    # First find a directory with `pyproject.toml`, `setup.cfg`, or `setup.py`
    root = _find_root_dir_with_file(root, ["pyproject.toml", "setup.cfg", "setup.py"])

    # It's likely that the root is the parent directory of the package,
    # but in some cases like multiple languages, mono-repo, etc. it may not be.
    for _ in range(3):
        dirname = root.name
        if dirname.startswith(parentdir_prefix):
            return VersionDict(
                {
                    "version": dirname[len(parentdir_prefix) :],
                    "full_revisionid": None,
                    "dirty": False,
                    "error": None,
                    "date": None,
                }
            )
        rootdirs.append(root)
        root = root.parent

    if verbose:
        print(
            f"Tried directories {rootdirs!s} but none started with prefix {parentdir_prefix}"
        )
    raise NotThisMethodError("rootdir doesn't start with parentdir_prefix")


def get_versions(cfg: "VersionPioneerConfig | None" = None) -> VersionDict:
    """Get version information or return default if unable to do so."""
    if cfg is None:
        cfg = VersionPioneerConfig()

    try:
        return _git_versions_from_keywords(
            _get_keywords(), cfg.tag_prefix, verbose=cfg.verbose
        )
    except NotThisMethodError:
        pass

    try:
        return GitPieces.from_vcs(
            cfg.tag_prefix, _CURRENT_DIR, verbose=cfg.verbose
        ).render(cfg.style)
    except NotThisMethodError:
        pass

    if cfg.parentdir_prefix is not None:
        try:
            return _versions_from_parentdir(
                cfg.parentdir_prefix, _CURRENT_DIR, verbose=cfg.verbose
            )
        except NotThisMethodError:
            pass

    return {
        "version": "0+unknown",
        "full_revisionid": None,
        "dirty": None,
        "error": "unable to compute version",
        "date": None,
    }


__version_dict__: VersionDict = get_versions()
__version__ = __version_dict__["version"]


if __name__ == "__main__":
    import json

    print(json.dumps(__version_dict__))
