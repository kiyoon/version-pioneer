from version_pioneer.api import exec_version_script


def get_version():
    return exec_version_script(output_format="version-string")
