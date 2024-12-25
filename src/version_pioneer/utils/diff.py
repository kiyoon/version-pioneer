from __future__ import annotations


def unidiff_output(expected: str, actual: str):
    """Returns a string containing the unified diff of two multiline strings."""
    import difflib

    expected_list = expected.splitlines(keepends=True)
    actual_list = actual.splitlines(keepends=True)

    diff = difflib.unified_diff(expected_list, actual_list)

    return "".join(diff)
