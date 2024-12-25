from __future__ import annotations

import contextlib
import subprocess
import sys
from io import StringIO
from os import PathLike
from pathlib import Path


def _run_module(*args, check=True):
    """
    Run python module like `python -m ...`.
    """
    process = subprocess.run(
        [sys.executable, "-m", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        check=check,
    )

    return process


def build_project(*args, cwd=None, check=True, use_uv=True):
    """
    By default, build both wheel and sdist. And just check the content of the wheel later.

    If the wheel is built correctly this way, the sdist should be correct as well. (project dir -> sdist -> wheel)
    But if you build them separately, the sdist is skipped so we can't be sure.
    """
    if not use_uv:
        # replace --out-dir with --outdir (pyproject-build uses --outdir)
        args = (arg if arg != "--out-dir" else "--outdir" for arg in args)
        process = _run_module("build", *args, check=check)
        output = process.stdout

    else:
        process = subprocess.run(
            ["uv", "build", *args],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=cwd,
        )
        output = process.stderr

    # Find Successfully built *.whl
    built_paths: list[Path] = []
    for line in output.splitlines():
        if line.startswith("Successfully built"):
            # if not wheel_path.is_absolute():
            #     # pyproject-build does not print absolute path
            #     wheel_path = Path(d) / wheel_path
            built_paths.append(Path(line.split()[2]))

    # if not built_paths:
    #     raise RuntimeError("Failed to build plugin")

    return process.stderr, built_paths


def unpack_wheel(wheel_path: str | PathLike, dest_dir: str | PathLike | None = None):
    from wheel.cli.unpack import unpack

    f = StringIO()
    with contextlib.redirect_stdout(f):
        unpack(str(wheel_path), str(dest_dir) if dest_dir else ".")
    return f.getvalue()
