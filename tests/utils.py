import subprocess
import sys

import pytest


def run(*args, check=True):
    process = subprocess.run(  # noqa: PLW1510
        [sys.executable, "-m", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if check and process.returncode:
        pytest.fail(process.stdout)

    return process.stdout


def build_project(*args, check=True):
    if not args:
        args = ["-w"]

    return run("build", *args, check=check)


def append(file, text):
    file.write_text(file.read_text() + text)
