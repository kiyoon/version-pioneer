from pathlib import Path

from version_pioneer.utils.versionscript import exec_versionscript


def test_exec_versionscript_default_to_utf8(tmp_path: Path):
    """Versionscript without encoding declaration is executed as UTF-8 by default."""
    versionscript = tmp_path / "_version.py"
    utf8_content = (
        'version_label = "2.0.0 ümlaut"\n'
        "\n"
        "def get_version_dict():\n"
        "    return {\n"
        '        "version": version_label,\n'
        "    }\n"
    )
    versionscript.write_text(utf8_content, encoding="utf-8")

    version_dict = exec_versionscript(versionscript)

    assert version_dict["version"] == "2.0.0 ümlaut"


def test_exec_versionscript_explicit_utf8(tmp_path: Path):
    """Versionscript with UTF-8 encoding is executed correctly."""
    versionscript = tmp_path / "_version.py"
    utf8_content = (
        "# -*- coding: utf-8 -*-\n"
        'version_label = "1.0.0 ñandú"\n'
        "\n"
        "def get_version_dict():\n"
        "    return {\n"
        '        "version": version_label,\n'
        "    }\n"
    )
    versionscript.write_text(utf8_content, encoding="utf-8")

    version_dict = exec_versionscript(versionscript)

    assert version_dict["version"] == "1.0.0 ñandú"


def test_exec_versionscript_non_utf8_source(tmp_path: Path):
    """Versionscript can declare a non-UTF-8 encoding and still be executed."""
    versionscript = tmp_path / "_version.py"
    non_utf8_content = (
        "# -*- coding: latin-1 -*-\n"
        'version_label = "0.9.0 café"\n'
        "\n"
        "def get_version_dict():\n"
        "    return {\n"
        '        "version": version_label,\n'
        "    }\n"
    )
    versionscript.write_text(non_utf8_content, encoding="latin-1")

    version_dict = exec_versionscript(versionscript)

    assert version_dict["version"] == "0.9.0 café"
