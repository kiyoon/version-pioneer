#!/usr/bin/env python3
"""
Generate a version number from Git tags (e.g. tag "v1.2.3" and 4 commits -> "1.2.3+4.g123abcdef" in "pep440" style).

This "versionscript" may be replaced with a much shorter "versionfile" in distribution tarballs
(built by `uv build`, `pyproject-build`) that just contains one method:
`def get_version_dict() -> VersionDict: return {"version": "0.1.0", ...}`.

Refactored from Versioneer's _version.py.

Note:
    - Should be compatible with python 3.8+ without any dependencies.
        - (For dev) Avoid importing third-party libraries, including version-pioneer itself
          because this file can get vendored into other projects.
        - (For user) Once the script is vendored, and you want to customise it, of course you can
          import other libraries and add those in build-time dependencies.
    - This file is usually located at `src/my_package/_version.py`.
    - `src/my_package/__init__.py` should define `__version__ = get_version_dict()["version"]` by importing this module.
    - It should also be able to be run as a script to print the version info in json format.
    - It is often `exec`-uted and `get_version_dict()` is evaluated from this file.
        - Using `from __future__ import ...` with dataclasses makes it hard to "exec" this file,
          so you MUST NOT use both here.
            - See https://github.com/mkdocs/mkdocs/issues/3141
              https://github.com/pypa/hatch/issues/1863
              https://github.com/sqlalchemy/alembic/issues/1419
            - You need to put the module in `sys.modules` before executing
              because dataclass will look for the type there.
            - While this can be fixed, it's a common gotcha and I expect that
              some build backends or tools will be buggy.
            - For now, we don't future import. In dataclass definition,
              we use `typing.Optional` instead of `| None`
              until we drop support for Python 3.9.
"""

# ruff: noqa: T201 FA100

import contextlib
import errno
import functools
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from email.parser import Parser
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict, TypeVar, Union


class VersionStyle(str, Enum):
    pep440 = "pep440"
    pep440_master = "pep440-master"
    pep440_branch = "pep440-branch"
    pep440_pre = "pep440-pre"
    pep440_post = "pep440-post"
    pep440_post_branch = "pep440-post-branch"
    git_describe = "git-describe"
    git_describe_long = "git-describe-long"
    digits = "digits"


VERSION_STYLE_TYPE = TypeVar(
    "VERSION_STYLE_TYPE",
    Literal[
        "pep440",
        "pep440-master",
        "pep440-branch",
        "pep440-pre",
        "pep440-post",
        "pep440-post-branch",
        "git-describe",
        "git-describe-long",
        "digits",
    ],
    VersionStyle,
)


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
    # Set it to None to try to determine the prefix from pyproject.toml.
    parentdir_prefix: Optional[str] = None
    verbose: bool = False


# ┌──────────────────────────────────────────┐
# │     Modify the configuration above.      │
# └──────────────────────────────────────────┘


class VersionDict(TypedDict):
    """Return type of get_version_dict()."""

    version: str
    full_revisionid: "str | None"
    dirty: "bool | None"
    error: "str | None"
    date: "str | None"


try:
    _SCRIPT_DIR_OR_CURRENT_DIR = Path(__file__).resolve().parent
except NameError:
    # NOTE: py2exe/bbfreeze/non-cpython implementations may not have __file__.
    # and usually during installation when this file is evaluated, __file__ doesn't exist.
    # However, once you installed in editable mode (e.g. `pip install -e .`),
    # __file__ will be available and more reliable.
    _SCRIPT_DIR_OR_CURRENT_DIR = Path.cwd()


MASTER_BRANCHES = ("master", "main")

if sys.platform == "win32":
    GIT_COMMANDS = ["git.cmd", "git.exe"]
else:
    GIT_COMMANDS = ["git"]

# GIT_DIR can interfere with correct operation of Versioneer.
# It may be intended to be passed to the Versioneer-versioned project,
# but that should not change where we get our version from.
env = os.environ.copy()
env.pop("GIT_DIR", None)


# https://github.com/pypa/packaging/blob/24.2/src/packaging/version.py#L117-L146
# Make parentdir-prefix only match version strings.
# Example:
#     the GitHub repo can be myprogram-python and the package name is myprogram,
#     leading to parse "python" as a version string.
#     So we restrict it to search myprogram-python-1.0.0 styled folders only.
# Note:
#     - The check passes version strings other than PEP440. This is good because there are projects other than Python.
#     - Use with re.VERBOSE: `re.match(_VERSION_PATTERN, "1.0.0", re.VERBOSE)`
_VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""


class NotThisMethodError(Exception):
    """Exception raised if a method is not valid for the current scenario."""


class CurrentBranchIsMasterError(Exception):
    """GitMasterDistance can't be initialised if the current branch is master."""


@dataclass(frozen=True)
class GitMasterDistance:
    """
    Compute the distance from the tag until master, and from master to current branch.

    Useful if you often create a develop branch from master.

    Relevant commands:
        ```console
        $ git branch --show-current
        feat/branch-name

        $ # use with -a to include remote branches
        $ git branch --contains <commit>
        * master
          feat/branch-name

        $ # Notice that there are no master (only the origin/master) in the list
        $ # because the master has more commits than the current branch.
        $ # Thus we can't use the '%D' ref names.
        $ # We instead use `git branch --contains` on each commit to find the branch.
        $ git log v0.3.2..[BRANCH] --pretty=format:"%H,%h,%D"  # BRANCH is optional (default: current branch)
        87e38450d1fce0398fbc9de08f2abe3e5da0431e,87e3845,trash/version
        8a76eac0f107dd3810c3cfd5c89e92c7f5d31e50,8a76eac,
        a855d640912f728b8946eddba41ed5b2a992f394,a855d64,origin/master, origin/HEAD
        5cb3c6663f494b3c99dfd23b5394fa2da7f49cef,5cb3c66,
        2c00c0ed4e46a5459bc70f47739a0c50a789d3c3,2c00c0e,
        812d3e29666f2d75b80b4160532fa25afaab2ffd,812d3e2,tag: v0.3.3
        2127fd373d14ed5ded497fc18ac1c1b667f93a7d,2127fd3,
        ae7cb503342d551e2503dc0a90be656946342743,ae7cb50,
        ```

    References:
        - https://stackoverflow.com/questions/4649356/how-do-i-run-git-log-to-see-changes-only-for-a-specific-branch
        - https://stackoverflow.com/questions/2706797/finding-what-branch-a-git-commit-came-from
        - https://stackoverflow.com/questions/3998883/git-how-to-find-commit-hash-where-branch-originated-from
            - The reason we can't use reflog..
    """

    current_branch: str
    distance_from_tag_to_master: int
    distance_from_master: int
    master_commit: str

    @property
    def master_commit_short(self) -> "str | None":
        """Return the short commit hash of the master commit."""
        if self.master_commit is not None:
            return self.master_commit[:7]
        return None

    @classmethod
    def from_git(
        cls: "type[GitMasterDistance]",
        tag_of_interest: "str | None",
        *,
        cwd: "str | PathLike",
        verbose: bool = False,
    ) -> "GitMasterDistance":
        git_runner = functools.partial(
            _run_git_command_or_error, env=env, verbose=verbose
        )

        # Get the current branch name
        current_branch, rc = git_runner(
            ["branch", "--show-current"],
            cwd=cwd,
        )
        current_branch = current_branch.strip()

        if current_branch in MASTER_BRANCHES:
            raise CurrentBranchIsMasterError(
                "Current branch is master. Can't compute distance to/from master."
            )

        if tag_of_interest is None:
            # Get entire history (commits) from the current branch
            out, rc = git_runner(
                ["log", "--pretty=format:%H"],
                cwd=cwd,
            )
        else:
            # Get history from the tag to the current branch
            out, rc = git_runner(
                ["log", f"{tag_of_interest}..", "--pretty=format:%H"],
                cwd=cwd,
            )

        all_commits = out.splitlines()

        # NOTE: all commits could be no output if the tag is the same as the current branch.

        # Search from the top, and find the first commit that shares the master branch
        distance_from_master = 0
        master_commit = None
        for commit in all_commits:
            out, rc = git_runner(
                ["branch", "--contains", commit],
                cwd=cwd,
            )
            branches = out.splitlines()
            # Strip off the leading "* " from the list of branches.
            branches = [branch.lstrip("* ") for branch in branches]
            if any(
                master_branch_name in branches for master_branch_name in MASTER_BRANCHES
            ):
                master_commit = commit
                break

            distance_from_master += 1

        if master_commit is None:
            # Can't find master? We assume that it's the tag. It may not always be. (like release branch)
            if tag_of_interest is None:
                if verbose:
                    print(
                        "No tag found and none of the commit history points to master/main."
                    )
                    print("Maybe detached head or you don't use master?")
                raise NotThisMethodError(
                    "No tag found and none of the commit history points to master/main. "
                    "Maybe detached head or you don't use master?"
                )

            out, re = git_runner(["rev-list", "-1", tag_of_interest], cwd=cwd)
            master_commit = out.strip()
            if len(master_commit) != 40:
                raise NotThisMethodError("Something is strange in you git commit hash")

        return cls(
            current_branch=current_branch,
            distance_from_tag_to_master=len(all_commits) - distance_from_master,
            distance_from_master=distance_from_master,
            master_commit=master_commit,
        )


@dataclass(frozen=True)
class GitPieces:
    """
    Get version from 'git describe' in the root of the source tree.

    This only gets called if _version.py hasn't already been rewritten with a short
    version string, meaning we're inside a checked out source tree.
    """

    long: str
    short: str
    branch: str
    dirty: bool

    # options to pass to GitMasterDistance
    cwd: Union[str, PathLike]
    verbose: bool

    error: Optional[str] = None
    distance: Optional[int] = None
    closest_fulltag: Optional[str] = None  # include tag_prefix (v1.0.0)
    closest_tag: Optional[str] = None  # strip tag_prefix (1.0.0)
    date: Optional[str] = None

    @classmethod
    def from_git(
        cls: "type[GitPieces]",
        tag_prefix: str,
        *,
        cwd: "str | PathLike",
        verbose: bool = False,
    ) -> "GitPieces":
        runner = functools.partial(_run_command, env=env, verbose=verbose)

        _, rc = runner(
            GIT_COMMANDS, ["rev-parse", "--git-dir"], cwd=cwd, hide_stderr=not verbose
        )
        if rc != 0:
            if verbose:
                print(f"Directory {cwd} not under git control")
            raise NotThisMethodError("'git rev-parse --git-dir' returned error")

        # if there is a tag matching tag_prefix, this yields TAG-NUM-gHEX[-dirty]
        # if there isn't one, this yields HEX[-dirty] (no NUM)
        describe_out, rc = runner(
            GIT_COMMANDS,
            [
                "describe",
                "--tags",
                "--dirty",
                "--always",
                "--long",
                "--match",
                f"{tag_prefix}[[:digit:]]*",
            ],
            cwd=cwd,
        )
        # --long was added in git-1.5.5
        if describe_out is None:
            raise NotThisMethodError("'git describe' failed")
        describe_out = describe_out.strip()
        full_out, rc = runner(GIT_COMMANDS, ["rev-parse", "HEAD"], cwd=cwd)
        if full_out is None:
            raise NotThisMethodError("'git rev-parse' failed")
        full_out = full_out.strip()

        pieces: dict[str, Any] = {}
        pieces["long"] = full_out
        pieces["short"] = full_out[:7]  # maybe improved later
        pieces["error"] = None

        branch_name, rc = runner(
            GIT_COMMANDS, ["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd
        )
        # --abbrev-ref was added in git-1.6.3
        if rc != 0 or branch_name is None:
            raise NotThisMethodError("'git rev-parse --abbrev-ref' returned error")
        branch_name = branch_name.strip()

        if branch_name == "HEAD":
            # If we aren't exactly on a branch, pick a branch which represents
            # the current commit. If all else fails, we are on a branchless
            # commit.
            branches, rc = runner(GIT_COMMANDS, ["branch", "--contains"], cwd=cwd)
            # --contains was added in git-1.5.4
            if rc != 0 or branches is None:
                raise NotThisMethodError("'git branch --contains' returned error")
            branches = branches.split("\n")

            # Remove the first line if we're running detached
            if "(" in branches[0]:
                branches.pop(0)

            # Strip off the leading "* " from the list of branches.
            branches = [branch.lstrip("* ") for branch in branches]
            if not branches:
                branch_name = None
            else:
                for master_branch_name in MASTER_BRANCHES:
                    if master_branch_name in branches:
                        branch_name = master_branch_name
                        break
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
                return cls(**pieces, cwd=cwd, verbose=verbose)

            # tag
            full_tag = mo.group(1)
            if not full_tag.startswith(tag_prefix):
                if verbose:
                    print(f"tag '{full_tag}' doesn't start with prefix '{tag_prefix}'")
                pieces["error"] = (
                    f"tag '{full_tag}' doesn't start with prefix '{tag_prefix}'"
                )
                return cls(**pieces, cwd=cwd, verbose=verbose)
            pieces["closest_fulltag"] = full_tag
            pieces["closest_tag"] = full_tag[len(tag_prefix) :]

            # distance: number of commits since tag
            pieces["distance"] = int(mo.group(2))

            # commit: short hex revision ID
            pieces["short"] = mo.group(3)

        else:
            # HEX: no tags
            pieces["closest_fulltag"] = None
            pieces["closest_tag"] = None
            out, rc = runner(
                GIT_COMMANDS, ["rev-list", "HEAD", "--left-right"], cwd=cwd
            )
            assert out is not None
            pieces["distance"] = len(out.split())  # total number of commits

        # commit date: see ISO-8601 comment in git_versions_from_keywords()
        out, rc = runner(GIT_COMMANDS, ["show", "-s", "--format=%ci", "HEAD"], cwd=cwd)
        assert out is not None
        date = out.strip()
        # Use only the last line.  Previous lines may contain GPG signature
        # information.
        date = date.splitlines()[-1]
        pieces["date"] = date.strip().replace(" ", "T", 1).replace(" ", "", 1)

        return cls(**pieces, cwd=cwd, verbose=verbose)

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

    def _render_pep440_master(self) -> str:
        """
        Render including master branch distance and commit like TAG[+MASTERDIST.gMASTERHEX.BRANCHDIST.gHEX[.dirty]].

        For example, 'v1.2.3+4.g1abcdef.5.g2345678'
        meaning 4 commits from v1.2.3 to master, and 5 commits from master to the current branch.

        Exceptions:
            1. no tags. git_describe was just HEX. 0+untagged.MASTERDISTANCE.gMASTERHEX.BRANCHDIST.gHEX[.dirty]
            2. current branch is master. Just like PEP440 style.
            3. if no master is found after the tag, we assume tag = master. (TAG+0.gTAGHEX.BRANCHDIST.gHEX[.dirty])
                - the logic is in GitMasterDistance.from_git()

        Note:
            - New in Version-Pioneer.
        """
        try:
            master_info = GitMasterDistance.from_git(
                tag_of_interest=self.closest_fulltag, cwd=self.cwd, verbose=self.verbose
            )
        except CurrentBranchIsMasterError:
            # exception #2
            return self._render_pep440()

        if (
            master_info.distance_from_tag_to_master == 0
            and master_info.distance_from_master == 0
        ):
            # Just the tag
            return self.closest_tag or "0+untagged"

        if self.closest_tag:
            rendered = self.closest_tag
            rendered += self._plus_or_dot
        else:
            # exception #1
            rendered = "0+untagged."

        rendered += (
            f"{master_info.distance_from_tag_to_master}.g{master_info.master_commit_short}"
            f".{master_info.distance_from_master}.g{self.short}"
        )

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
                if self.branch not in MASTER_BRANCHES:
                    rendered += ".dev0"
                rendered += self._plus_or_dot
                rendered += f"{self.distance}.g{self.short}"
                if self.dirty:
                    rendered += ".dirty"
        else:
            # exception #1
            rendered = "0"
            if self.branch not in MASTER_BRANCHES:
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
        TAG[.postDISTANCE+gHEX[.dirty]] .

        Note:
            Difference from versioneer is that .dev0 used to be used for .dirty. Their note:

            > TAG[.postDISTANCE[.dev0]+gHEX] .
            >
            > The ".dev0" means dirty. Note that .dev0 sorts backwards
            > (a dirty tree will appear "older" than the corresponding clean one),
            > but you shouldn't be releasing software with -dirty anyways.

        Exceptions:
            When no tags: 0.postDISTANCE+gHEX[.dirty]
        """
        if self.closest_tag:
            rendered = self.closest_tag
            if self.distance or self.dirty:
                rendered += f".post{self.distance}"
                rendered += self._plus_or_dot
                rendered += f"g{self.short}"
                if self.dirty:
                    rendered += ".dirty"
        else:
            # exception
            rendered = f"0.post{self.distance}"
            rendered += f"+g{self.short}"
            if self.dirty:
                rendered += ".dirty"
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
                if self.branch not in MASTER_BRANCHES:
                    rendered += ".dev0"
                rendered += self._plus_or_dot
                rendered += f"g{self.short}"
                if self.dirty:
                    rendered += ".dirty"
        else:
            # exception #1
            rendered = f"0.post{self.distance}"
            if self.branch not in MASTER_BRANCHES:
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
                - Chrome extension version should not have more than 4 segments,
                  so make sure the tags are up to 3 segments.
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
        elif style == "pep440-master":
            rendered = self._render_pep440_master()
        elif style == "pep440-branch":
            rendered = self._render_pep440_branch()
        elif style == "pep440-pre":
            rendered = self._render_pep440_pre()
        elif style == "pep440-post":
            rendered = self._render_pep440_post()
        elif style == "pep440-post-branch":
            rendered = self._render_pep440_post_branch()
        elif style == "git-describe":
            rendered = self._render_git_describe()
        elif style == "git-describe-long":
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


def _run_git_command_or_error(
    args: "list[str | PathLike]",
    *,
    cwd: "str | PathLike | None" = None,
    env: "dict[str, str] | None" = None,
    verbose: bool = False,
):
    """Run a git command or raise an error."""
    out, rc = _run_command(
        GIT_COMMANDS, args, cwd=cwd, hide_stderr=not verbose, env=env, verbose=verbose
    )

    if rc != 0 or out is None:
        raise NotThisMethodError(f"'git {' '.join(map(str, args))}' returned error")
    return out, rc


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


def get_version_from_parentdir(
    parentdir_prefix: "str | None", cwd: "str | PathLike", *, verbose: bool = False
) -> VersionDict:
    """
    Try to determine the version from the parent directory name.

    Source tarballs conventionally unpack into a directory that includes both the project name and a version string.

    If parentdir_prefix is None, it will try to determine the parentdir_prefix from pyproject.toml.
    """
    rootdirs = []

    # First find a directory with `pyproject.toml`, `setup.cfg`, or `setup.py`

    try:
        root = _find_root_dir_with_file(
            cwd, ["pyproject.toml", "setup.cfg", "setup.py"]
        )
    except FileNotFoundError as e:
        raise NotThisMethodError from e

    def try_parentdir(
        project_root: Path, parentdir_prefix: str
    ) -> "VersionDict | None":
        # It's likely that the root is the parent directory of the package,
        # but in some cases like multiple languages, mono-repo, etc. it may not be.
        for _ in range(3):
            dirname = project_root.name
            if dirname.startswith(parentdir_prefix):
                version_candidate = dirname[len(parentdir_prefix) :]
                if re.match(_VERSION_PATTERN, version_candidate, re.VERBOSE):
                    return {
                        "version": version_candidate,
                        "full_revisionid": None,
                        "dirty": False,
                        "error": None,
                        "date": None,
                    }
            rootdirs.append(project_root)

            if project_root.parent.samefile(project_root):
                break
            project_root = project_root.parent

        return None

    def get_prefix_from_source_url(source_url: str) -> "str | None":
        if not source_url.startswith(
            "https://github.com/"
        ) and not source_url.startswith("https://gitlab.com/"):
            return None

        # Remove trailing .git
        if source_url.endswith(".git"):
            source_url = source_url[:-4]

        # Last part of the URL plus a hyphen
        return source_url.split("/")[-1] + "-"

    def try_parentdir_from_source_url(source_url: str) -> "VersionDict | None":
        prefix = get_prefix_from_source_url(source_url)
        if prefix:
            version_dict = try_parentdir(root, prefix)
            if version_dict:
                return version_dict
        return None

    def try_all_parentdir_in_pyproject_toml(pyproject: dict) -> "VersionDict | None":
        with contextlib.suppress(KeyError):
            version_dict = try_parentdir_from_source_url(
                pyproject["project"]["urls"]["homepage"]
            )
            if version_dict:
                return version_dict
        with contextlib.suppress(KeyError):
            version_dict = try_parentdir_from_source_url(
                pyproject["project"]["urls"]["Homepage"]
            )
            if version_dict:
                return version_dict
        with contextlib.suppress(KeyError):
            version_dict = try_parentdir_from_source_url(
                pyproject["project"]["urls"]["source"]
            )
            if version_dict:
                return version_dict
        with contextlib.suppress(KeyError):
            version_dict = try_parentdir_from_source_url(
                pyproject["project"]["urls"]["Source"]
            )
            if version_dict:
                return version_dict
            return None
        with contextlib.suppress(KeyError):
            return try_parentdir(root, pyproject["project"]["name"] + "-")

    if parentdir_prefix is None:
        # NOTE: New in Version-Pioneer
        # Automatically determine the parentdir_prefix from pyproject.toml
        # 1. project.urls.Homepage
        # homepage / Homepage / source / Source -> if https://github.com/ -> remove trailing .git
        """
        # numpy example
        [project.urls]
        homepage = "https://numpy.org"
        documentation = "https://numpy.org/doc/"
        source = "https://github.com/numpy/numpy"
        download = "https://pypi.org/project/numpy/#files"
        tracker = "https://github.com/numpy/numpy/issues"
        "release notes" = "https://numpy.org/doc/stable/release"
        """
        # NOTE: 2. project.name
        """
        [project]
        name = "version-pioneer"
        """

        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib
        except ModuleNotFoundError as e:
            if verbose:
                print(
                    "tomli not found. Please install tomli or use Python 3.11 to "
                    "automatically determine the parentdir_prefix from pyproject.toml"
                )
            raise NotThisMethodError(
                "tomli not found. Please install tomli or use Python 3.11 to "
                "automatically determine the parentdir_prefix from pyproject.toml"
            ) from e
        with open(root / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        version_dict = try_all_parentdir_in_pyproject_toml(pyproject)
    else:
        version_dict = try_parentdir(root, parentdir_prefix)

    if version_dict:
        return version_dict

    if verbose:
        print(
            f"Tried directories {rootdirs!s} but none started with prefix {parentdir_prefix or '<auto>'}"
        )
    raise NotThisMethodError("rootdir doesn't start with parentdir_prefix")


def get_version_from_pkg_info(cwd: "str | PathLike") -> VersionDict:
    """
    Parse PKG-INFO file if it exists, because it's the most reliable way
    to get the version from an sdist (`build --sdist`)
    since sdist would not have a git information.

    This matters if you choose to "NOT" write the versionfile.

    i.e. [tool.version-pioneer]
         versionscript = src/my_package/_version.py
         # versionfile-sdist = NOT DEFINED

    Note:
        - New in Version-Pioneer
        - Hatchling's Version Source Plugin is deactivated when PKG-INFO is present, so this method would not matter.
        - Only for other backends like setuptools.
    """
    try:
        project_root = _find_root_dir_with_file(cwd, "PKG-INFO")
    except FileNotFoundError:
        raise NotThisMethodError("PKG-INFO not found")  # noqa: B904
    else:
        pyproject_toml = project_root / "pyproject.toml"
        if not pyproject_toml.exists():
            raise NotThisMethodError(
                "PKG-INFO found but no pyproject.toml found in the project root"
            )

        # Confirm [tool.version-pioneer] section exists in pyproject.toml
        with open(pyproject_toml) as f:
            lines = f.readlines()
        for line in lines:
            if "[tool.version-pioneer]" in line:
                break
        else:
            raise NotThisMethodError(
                "[tool.version-pioneer] section not found in pyproject.toml"
            )

        # Read PKG-INFO file
        with open(project_root / "PKG-INFO") as f:
            pkg_info = Parser().parse(f)
        pkg_version = pkg_info.get("Version")
        if not pkg_version:
            raise NotThisMethodError("Version not found in PKG-INFO")

        return {
            "version": pkg_version,
            "full_revisionid": None,
            "dirty": False,
            "error": None,
            "date": None,
        }


def get_version_dict_with_all_methods(
    cfg: "VersionPioneerConfig | None" = None, *, cwd: "str | PathLike | None" = None
) -> VersionDict:
    """
    Get version information from PKG-INFO, Git tags or parent directory as a fallback.
    """
    if cfg is None:
        cfg = VersionPioneerConfig()

    if cwd is None:
        cwd = _SCRIPT_DIR_OR_CURRENT_DIR

    try:
        return get_version_from_pkg_info(cwd)
    except NotThisMethodError:
        pass

    try:
        return GitPieces.from_git(cfg.tag_prefix, cwd=cwd, verbose=cfg.verbose).render(
            cfg.style
        )
    except NotThisMethodError:
        pass

    try:
        return get_version_from_parentdir(
            cfg.parentdir_prefix, cwd, verbose=cfg.verbose
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


# IMPORTANT: However you customise the file, make sure the following function is defined!
def get_version_dict() -> VersionDict:
    return get_version_dict_with_all_methods()


if __name__ == "__main__":
    import json

    print(json.dumps(get_version_dict()))
