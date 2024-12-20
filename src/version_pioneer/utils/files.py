from __future__ import annotations

import filecmp
import fnmatch
import os
from collections.abc import Iterable, Sequence
from os import PathLike
from pathlib import Path


def remove_files_recusively(directory: str | PathLike, patterns: str | Sequence[str]):
    """Remove files recursively from a directory that match any of the patterns."""
    patterns = [patterns] if isinstance(patterns, str) else patterns

    for root, _, files in os.walk(directory):
        root = Path(root)
        for file in files:
            if any(fnmatch.fnmatch(str(root / file), pattern) for pattern in patterns):
                (root / file).unlink()


def are_dir_trees_equal(dir1, dir2):
    """
    Compare two directories recursively. Files in each directory are
    assumed to be equal if their names and contents are equal.
    """
    dirs_cmp = filecmp.dircmp(dir1, dir2)
    if (
        len(dirs_cmp.left_only) > 0
        or len(dirs_cmp.right_only) > 0
        or len(dirs_cmp.funny_files) > 0
    ):
        raise FileNotFoundError(
            f"Directory trees are not equal: {dirs_cmp.left_only}, {dirs_cmp.right_only}, {dirs_cmp.funny_files}"
        )
    (_, mismatch, errors) = filecmp.cmpfiles(
        dir1, dir2, dirs_cmp.common_files, shallow=False
    )
    if len(mismatch) > 0 or len(errors) > 0:
        raise FileNotFoundError(f"Directory trees are not equal: {mismatch}, {errors}")
    for common_dir in dirs_cmp.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)  # noqa: PTH118
        new_dir2 = os.path.join(dir2, common_dir)  # noqa: PTH118
        are_dir_trees_equal(new_dir1, new_dir2)


def find_root_dir_with_file(
    source: str | PathLike, marker: str | Iterable[str]
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
