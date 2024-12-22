# 🧗🏽 Version-Pioneer: General-Purpose Versioneer for Any Build Backends

## Background

[Versioneer](https://github.com/python-versioneer/python-versioneer) finds the closest git tag like `v1.2.3` and generates a version string like `1.2.3+4.gxxxxxxx.dirty`.

- `1.2.3` is the closest git tag.
- `+4` is the number of commits since the tag.
- `gxxxxxxx` is the git commit hash (without the leading `g`).
- `.dirty` is appended if the working directory is dirty (i.e. has uncommitted changes).

[setuptools-scm](https://github.com/pypa/setuptools-scm) is a similar tool, but with some differences:

- How the version string is rendered: `1.2.3+4.gxxxxxxx.dirty` vs `1.2.4.dev4+gxxxxxxx`
    - No `.dirty` in setuptools-scm.
    - Infer the next version number (i.e. 1.2.4 instead of 1.2.3).
- The `_version.py` file is always a constant in setuptools-scm.
    - Versioneer can dynamically generate the version string at runtime, so it's always up-to-date. Useful for development (pip install -e .).
    - Setuptools-scm won't ever change the version string after installation. You need to reinstall to update the version string.


## ❓ Why this fork?

I have used versioneer for years, and I like the format and dynamic resolution of versions for development. However,

1. It doesn't support any build backends other than `setuptools` (like `pdm`, `hatchling`, `poetry`, `maturin`, `scikit-build`, etc.)
2. It doesn't support projects that are not Python (like Rust, Chrome Extension, etc.).

Every time I had to figure out how to integrate a new VCS versioning plugin but they all work differently and produce different version strings. GitHub Actions and other tools may not work with all different version format. Different language usually expects different format, and it's especially hard to make it compatible for mixed language projects.

The original versioneer is 99% boilerplate code to make it work with all legacy setuptools configurations. But the core functionality is simple: just get version from git tag and format it. I had to leverage this logic to integrate Versioneer in every project I had.

**🧗🏽  Version-Pioneer is a general-purpose Versioneer that works with any language and any build system.**

- **Highly customisable**: It's a easy-to-read script. Literally a simple python script which you can customise version format or anything as you need.
- Runs with Python 3.8+
- No dependencies like package, config file etc. It runs with one python file. 
- Works with any build backend with hooks.
- Works with any language, not just Python.
- Support for new version formats like `"digits"` that generates digits-only version string like `1.2.3.4`. Useful for multi-language projects, Chrome Extension, etc. because their versioning standard is different.

## 🚦 Usage (with build backend plugins) 

For `setuptools`, `hatchling` and `pdm-backend`, you can configure using the provided plugins. Below section describe how they work, so you can customise the behaviour by making your own hook as well, if you wish!

1. Configure `pyproject.toml`. `[tool.version-pioneer]` section is required.

```toml
[tool.version-pioneer]
versionfile-source = "src/my_project/_version.py"
versionfile-build = "my_project/_version.py"
```

2. Copy-paste [`src/version_pioneer/_version.py`](src/version_pioneer/_version.py) to your project.
    - You can use the CLI to install. Read [#version-pioneer-cli](#-version-pioneer-cli) section.  
    ```bash
    version-pioneer install
    ```
3. Customise `_version.py` to your needs. For example, style of the version string can be configured in `class VersionPioneerConfig`.
4. Configure your build backend to execute `_version.py` and use the version string. For example, Hatchling and PDM are supported.

📦 Setuptools:

```toml
# append to pyproject.toml
[build-system]
requires = ["setuptools", "version-pioneer"]
build-backend = "setuptools.build_meta"
```

`setup.py`:

```python
from setuptools import setup
from version_pioneer.build.setuptools import get_cmdclass, get_version

setup(
    version=get_version(),
    cmdclass=get_cmdclass(),
)
```

🥚 Hatchling:

```toml
# append to pyproject.toml
[build-system]
requires = ["hatchling", "version-pioneer"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "code"
path = "src/my_project/_version.py"
expression = "__version__"  # default

[tool.hatch.build.hooks.version-pioneer]
# section is empty because we read config from `[tool.version-pioneer]` section.
```

PDM:

```toml
# append to pyproject.toml
[build-system]
requires = ["pdm-backend", "version-pioneer"]
build-backend = "pdm.backend"
```

## 🛠️ Configuration

Unlike Versioneer, the configuration is located in two places: `pyproject.toml` and `src/my_project/_version.py`. This is to make it less confusing, because in Versioneer, most of the pyproject.toml config is actually useless once you install `_version.py` in your project.

### pyproject.toml [tool.version-pioneer]

Configuration for build backends (and Version-Pioneer CLI if you want to use it). 

- `versionfile-source`: Path to the `_version.py` file in your project. (e.g. `src/my_project/_version.py`)
- `versionfile-build`: Path to the `_version.py` file in build directory. (e.g. `my_project/_version.py`)


The idea is that it just tells you where it is, and the other configs should be parsed directly from `_version.py`.

### `_version.py`

Configuration for resolving the version string.

This file has to be able to run like a script without any other dependencies (like package, files, config, etc.).

```python
@dataclass(frozen=True)
class VersionPioneerConfig:
    style: VersionStyle = VersionStyle.pep440
    tag_prefix: str = "v"
    parentdir_prefix: Optional[str] = None
    verbose: bool = False
```

- `style`: similar to Versioneer's `style` option. Two major styles are:
    - `VersionStyle.pep440`: "1.2.3+4.gxxxxxxx.dirty" (default)
    - `VersionStyle.digits`: "1.2.3.5"
        - Digits-only version string.
        - The last number is the distance from the tag (dirty is counted as 1, thus 5 in this example).
        - Useful for multi-language projects, Chrome Extension, etc.
    - See Versioneer for more styles (or read documentation in _version.py).
- `tag_prefix`: tag to look for in git for the reference version.
- `parentdir_prefix`: if there is no .git, like it's a source tarball downloaded from GitHub Releases, find version from the name of the parent directory. e.g. setting it to "github-repo-name-" will find the version from "github-repo-name-1.2.3"
- `verbose`: print debug messages.


## 💡 Understanding Version-Pioneer

It's important to understand how Version-Pioneer works, so you can customise it to your needs.

### Basic: _version.py as a script

The core functionality is in one file: [`_version.py`](src/version_pioneer/_version.py). This code is either used as a script (`python _version.py`) that prints a json of all useful information, or imported as a module (`from _version import __version__`), depending on your needs. The code looks something like this:

```python
# pseudo code of _version.py, original.
def get_version_dict(cfg = None, cwd = None):
    # Some logic to get the version string from git.
    # Read the source code. You can easily understand and customise it.
    ...

__version_dict__ = get_version_dict()
__version__ = __version_dict__["version"]

if __name__ == "__main__":
    import json

    print(json.dumps(__version_dict__))
```

Run it in your project to see what it prints. Change git tags, commit, and see how it changes.

```console
$ git tag v1.2.3
$ python _version.py
{"version": "1.2.3", "full_revisionid": "xxxxxx", "dirty": False, "error": None, "date": "2024-12-17T12:25:42+0900"}
$ git commit --allow-empty -m "commit"
$ python _version.py
{"version": "1.2.3+1.gxxxxxxx", "full_revisionid": "xxxxxx", "dirty": True, "error": None, "date": "2024-12-17T12:25:42+0900"}
```

### Basic: converting _version.py to a constant version string (for build)

For build, you would lose the git history, so you need to convert the `_version.py` to a constant version string.  
Just `exec` the original `_version.py` and save the result as you wish: text, json, etc.

```python
# code to evaluate __version_dict__ from the original _version.py
Path("src/my_project/_version.py").read_text()
module_globals = {}
exec(version_py, module_globals)
print(module_globals["__version_dict__"])
```

### Basic: building a Python package (replacing _version.py to a constant)

Copy-paste [`src/version_pioneer/_version.py`](src/version_pioneer/_version.py) to your project (like `src/my_project/_version.py`). When you install your package like `pip install -e .`, the code is unchanged, so it will always print up-to-date version string from git tags.

However, if you install like `pip install .` or `pyproject-build`, `uv build` etc., you would lose the git history so the `src/my_project/_version.py` should change.  
The original file is replaced with this. This is generated by literally executing the above file and saving version_dict as a constant.

```python
# pseudo code of _version.py, generated.
__version_dict__ = {
    "version": "0.3.2+15.g2127fd3.dirty",
    "full-revisionid": "2127fd373d14ed5ded497fc18ac1c1b667f93a7d",
    "dirty": True,
    "error": None,
    "date": "2024-12-17T12:25:42+0900",
}
__version__ = version_dict["version"]

if __name__ == "__main__":
    import json

    print(json.dumps(__version_dict__))
```

### Advanced: Configuring a 🥚 Hatchling Hook

Even if you are not familiar with Hatchling, hear me out. It is very straightforward.

Add hatchling configuration to `pyproject.toml`.

```toml
[build-system]
requires = ["hatchling", "tomli ; python_version < '3.11'"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "code"
path = "src/my_project/_version.py"
expression = "__version__"  # default

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"

[tool.version-pioneer]
versionfile-source = "src/my_project/_version.py"
versionfile-build = "my_project/_version.py"

[project]
name = "my-project"
dynamic = ["version"]
```

Basically you are telling Hatchling to execute `src/my_project/_version.py` and use `__version__` as the version string.

Add `hatch_build.py` to the project root.

```python
from __future__ import annotations

import stat
import sys
import tempfile
import textwrap
from os import PathLike
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


def load_toml(file: str | PathLike) -> dict[str, Any]:
    with open(file, "rb") as f:
        return tomllib.load(f)


class CustomPioneerBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            return

        pyproject_toml = load_toml(Path(self.root) / "pyproject.toml")

        # evaluate the original _version.py file to get the computed version
        versionfile_source = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionfile-source"]
        )
        version_py = versionfile_source.read_text()
        module_globals = {}
        exec(version_py, module_globals)

        # replace the file with the constant version
        self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
        self.temp_version_file.write(
            textwrap.dedent(f"""
                #!/usr/bin/env python3
                # This file is generated by version-pioneer
                # by evaluating the original _version.py file and storing the computed versions as a constant.

                __version_dict__ = {module_globals["__version_dict__"]}
                __version__ = __version_dict__["version"]
                
                if __name__ == "__main__":
                    import json

                    print(json.dumps(__version_dict__))
            """).strip()
        )
        self.temp_version_file.flush()

        # make it executable
        versionfile_build = Path(self.temp_version_file.name)
        versionfile_build.chmod(versionfile_build.stat().st_mode | stat.S_IEXEC)

        build_data["force_include"][self.temp_version_file.name] = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionfile-build"]
        )

    def finalize(
        self,
        version: str,
        build_data: dict[str, Any],
        artifact_path: str,
    ) -> None:
        if version != "editable":
            # Delete the temporary version file
            self.temp_version_file.close()
```

It just replaces the `_version.py` file with a constant version string. The version string is computed by evaluating the original `_version.py` file.
This is skipped when the project is installed in editable mode (`pip install -e .`).

Now you can install your package with `pip install .`, `pip install -e .`, or build a wheel with `hatch build` or `uv build`.

### Advanced: Configuring a PDM backend hook

The idea is the same, but the PDM doesn't really evaluate a code to get a version string (or maybe it doesn't work in this case).
So we do both in the hook.

📄 pyproject.toml:

```toml
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[tool.pdm.build]
custom-hook = "pdm_build.py"

[tool.version-pioneer]
versionfile-source = "src/my_project/_version.py"
versionfile-build = "my_project/_version.py"

[project]
name = "my-project"
dynamic = ["version"]
```

🐍 pdm_build.py:

```python
import stat
import textwrap
from pathlib import Path

from pdm.backend.hooks.base import Context


def pdm_build_initialize(context: Context):
    # Update metadata version
    versionfile_source = Path(
        context.config.data["tool"]["version-pioneer"]["versionfile-source"]
    )
    versionfile_code = versionfile_source.read_text()
    version_module_globals = {}
    exec(versionfile_code, version_module_globals)
    context.config.metadata["version"] = version_module_globals["__version__"]

    # Write the static version file
    if context.target != "editable":
        versionfile_build = context.build_dir / Path(
            context.config.data["tool"]["version-pioneer"]["versionfile-build"]
        )
        context.ensure_build_dir()
        versionfile_build.parent.mkdir(parents=True, exist_ok=True)
        versionfile_build.write_text(
            textwrap.dedent(f"""
                #!/usr/bin/env python3
                # This file is generated by version-pioneer
                # by evaluating the original _version.py file and storing the computed versions as a constant.

                __version_dict__ = {version_module_globals["__version_dict__"]}
                __version__ = __version_dict__["version"]

                if __name__ == "__main__":
                    import json

                    print(json.dumps(__version_dict__))
            """).strip()
        )
        # make it executable
        versionfile_build.chmod(versionfile_build.stat().st_mode | stat.S_IEXEC)
```

## 🚀 Version-Pioneer CLI

The above usage should be completely fine, but we do have a CLI tool to help you install and evaluate _version.py.

```bash
# Install with pip
pip install 'version-pioneer[cli]'

# Install with uv tool (in a separate environment, just for the CLI)
uv tool install 'version-pioneer[cli]'
```


### `version-pioneer install`: Install _version.py to your project

1. Configure `pyproject.toml` with `[tool.version-pioneer]` section.

```toml
[tool.version-pioneer]
versionfile-source = "src/my_project/_version.py"
versionfile-build = "my_project/_version.py"
```

2. `version-pioneer install` will copy-paste the `_version.py` to the path you specified.


### `version-pioneer exec-version-py`: Resolve _version.py and get the version

```console
$ version-pioneer

 Usage: version-pioneer [OPTIONS] COMMAND [ARGS]...

 🧗 Version-Pioneer: Dynamically manage project version with hatchling and pdm support.

╭─ Commands ────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ install                 Install _version.py at `tool.version-pioneer.versionfile-source` in pyproject.toml.   │
│ print-version-py-code   Print the content of _version.py file (for manual installation).                      │
│ exec-version-py         Resolve the _version.py file for build, and print the content.                        │
│ get-version-builtin     WITHOUT using the _version.py file, get version with Version-Pioneer logic.           │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Examples:

```console
$ version-pioneer exec-version-py --output-format version-string
0.1.0+8.g6228bc4.dirty

$ version-pioneer exec-version-py --output-format json
{"version": "0.1.0+8.g6228bc4.dirty", "full_revisionid": "6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f", "dirty": true, "error": null, "date": "2024-12-21T21:03:48+0900"}

$ version-pioneer exec-version-py --output-format python
#!/usr/bin/env python3
# GENERATED BY version-pioneer-v0.1.0
# by evaluating the original _version.py file and storing the computed versions as a constant.

__version_dict__ = {'version': '0.1.0+8.g6228bc4.dirty', 'full_revisionid': '6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f', 'dirty': True, 'error': None, 'date': '2024-12-21T21:03:48+0900'}
__version__ = __version_dict__["version"]

if __name__ == "__main__":
    import json

    print(json.dumps(__version_dict__))
```

### `version-pioneer get-version-builtin`: Get version without using _version.py

This is useful when you want to get the version string without using the `_version.py` file, like your project is probably not Python.

```console
$ version-pioneer get-version-builtin
0.1.0+8.g6228bc4.dirty

$ version-pioneer get-version-builtin --output-format json
{"version": "0.1.0+8.g6228bc4.dirty", "full_revisionid": "6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f", "dirty": true, "error": null, "date": "2024-12-21T21:03:48+0900"}

$ version-pioneer get-version-builtin --style digits
0.1.0.9
```


## 📚 Note

- Only supports git.
- `git archive` is not supported. Original Versioneer uses `.gitattributes` to tell git to replace some strings in `_version.py` when archiving. But this is not enough information (at least in my case) and the version string always becomes `0+unknown`. So I dropped it.
