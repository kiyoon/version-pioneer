from version_pioneer.api import exec_versionscript_and_convert


def get_version():
    return exec_versionscript_and_convert(output_format="version-string")
