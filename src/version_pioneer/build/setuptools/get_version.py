from version_pioneer.api import exec_version_py


def get_version():
    return exec_version_py(output_format="version-string")
