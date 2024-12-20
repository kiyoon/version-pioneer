from version_pioneer.api import exec_version_script_and_convert


def get_version():
    return exec_version_script_and_convert(output_format="version-string")
