# 🧗🏽 Version-Pioneer: General-Purpose Versioneer for Any Build Backends

![build](https://github.com/kiyoon/version-pioneer/actions/workflows/deploy.yml/badge.svg)

[![image](https://img.shields.io/pypi/v/version-pioneer.svg)](https://pypi.python.org/pypi/version-pioneer)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/version-pioneer)](https://pypistats.org/packages/version-pioneer)
[![image](https://img.shields.io/pypi/l/version-pioneer.svg)](https://pypi.python.org/pypi/version-pioneer)
[![image](https://img.shields.io/pypi/pyversions/version-pioneer.svg)](https://pypi.python.org/pypi/version-pioneer)

|  |  |
|--|--|
|[![Ruff](https://img.shields.io/badge/Ruff-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/astral-sh/ruff) |[![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Style%20checking/badge.svg)](https://github.com/kiyoon/version-pioneer/actions)|
| [![Ruff](https://img.shields.io/badge/Ruff-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/astral-sh/ruff) | [![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Linting/badge.svg)](https://github.com/kiyoon/version-pioneer/actions) |
| [![pytest](https://img.shields.io/badge/pytest-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/pytest-dev/pytest) [![doctest](https://img.shields.io/badge/doctest-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://docs.python.org/3/library/doctest.html) | [![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Tests/badge.svg)](https://github.com/kiyoon/version-pioneer/actions) |
| [![uv](https://img.shields.io/badge/uv-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/astral-sh/uv) | [![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Check%20pip%20compile%20sync/badge.svg)](https://github.com/kiyoon/version-pioneer/actions) |

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

The original versioneer is 99% boilerplate code to make it work with all legacy setuptools configurations, trying to "generate" code depending on the configuration, etc.. But the core functionality is simple: just get version from git tag and format it. I had to leverage this logic to integrate Versioneer in every project I had.

**🧗🏽  Version-Pioneer is a general-purpose Versioneer that works with any language and any build system.**

- **Highly customisable**: It's a easy-to-read script. Literally a simple python script which you can customise version format or anything as you need.
- Runs with Python 3.8+
- No dependencies like package, config file etc. It runs with one python file. 
- Works with any build backend with hooks.
- Works with any language, not just Python.
- Support for new version formats like `"digits"` that generates digits-only version string like `1.2.3.4`. Useful for multi-language projects, Chrome Extension, etc. because their versioning standard is different.
- Complete non-vendored mode support. With the original Versioneer you still had to install a `_version.py` script in your project, but Version-Pioneer is able to be installed as a package.
    ```python
    from pathlib import Path

    from version_pioneer.vcs import get_version_dict_from_vcs, VersionPioneerConfig


    def get_version_dict():
        cfg = VersionPioneerConfig(
            style="pep440",
            tag_prefix="v",
            parentdir_prefix=None,
            verbose=False,
        )

        return get_version_dict_from_vcs(cfg, cwd=Path(__file__).parent)
    ```


## 🏃 Quick Start (script not vendored, with build backend plugins)

For `setuptools`, `hatchling` and `pdm-backend`, you can configure using the provided plugins. Below section describe how they work, so you can customise the behaviour by making your own hook as well, if you wish!

1. Configure `pyproject.toml`. `[tool.version-pioneer]` section is required.

```toml
[tool.version-pioneer]
versionscript-source = "src/my_project/_version.py"  # Where to read the Version-Pioneer script (to execute `get_version_dict(*args, **kargs)`).
versionfile-source = "src/my_project/_version.py"  # Where to write the version string for sdist.
versionfile-build = "my_project/_version.py"  # Where to write the version string for wheel.
```

2. Create `src/my_project/_version.py` with `get_version_dict()` in your project.

```python
from pathlib import Path

from version_pioneer import get_version_dict_from_vcs, VersionPioneerConfig


def get_version_dict():
    cfg = VersionPioneerConfig(
        style="pep440",
        tag_prefix="v",
        parentdir_prefix=None,
        verbose=False,
    )

    return get_version_dict_from_vcs(cfg, cwd=Path(__file__).parent)
```

3. Put the following code in your project's `__init__.py` to use the version string.

```python
# src/my_project/__init__.py
from ._version import get_version_dict

__version__ = get_version_dict()["version"]
```

4. Configure your build backend to execute `_version_pioneer.py` and use the version string. Setuptools, Hatchling and PDM are supported.

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
path = "src/my_project/_version.py"  # Instaed of using __init__.py, calling _version.py is easier because it is designed to be executed standalone.
expression = "get_version_dict()['version']"

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

Voila! The version string is now dynamically generated from git tags, and the `_version.py` file is replaced with a constant version string when building a wheel or source distribution.

> [!TIP]
> The `_version.py` gets replaced to a constant version file when you build your package, so `version-pioneer` shouldn't be in your package dependencies.
> Instead, you may put it as a "dev dependency" in your `pyproject.toml`.
>
> ```toml
> [project.optional-dependencies]
> dev = ["version-pioneer"]
> ```
>
> Your package could be installed with `pip install -e '.[dev]'` for development.
>
> Or simply copy-paste the [`src/version_pioneer/version_pioneer_core.py`](src/version_pioneer/version_pioneer_core.py) script to your project to remove the dependency
> completely. This can be done with `version-pioneer install` or `version-pioneer print-script` CLI command.

<!-- 2. Copy-paste [`src/version_pioneer/_version_pioneer.py`](src/version_pioneer/_version_pioneer.py) to your project. -->
<!--     - You can use the CLI to install. Read [#version-pioneer-cli](#-version-pioneer-cli) section.   -->
<!--     ```bash -->
<!--     version-pioneer install-script -->
<!--     ``` -->
<!-- 3. Customise `_version_pioneer.py` to your needs. For example, style of the version string can be configured in `class VersionPioneerConfig`. -->
<!-- 5. You can use the version string by importing from `_version_pioneer.py` or `_version.py` in your project. -->



<!-- > [!TIP] -->
<!-- > **Why would you consider including both the script and the generated constant version file in the distributed package?** -->
<!-- > - It ensures consistency between development and distribution, simplifying the behavior for the dev. -->
<!-- > - It eliminates concerns about complex logic when building a wheel, which can involve sequential builds (e.g., project -> sdist -> wheel), reducing potential bugs. -->
<!-- > - Devs may want to import components like *type definitions*, *configuration*, etc., from the script. -->
<!-- > - IT'S NOT MANDATORY; we still support replacing the script with the generated version file. Simply set `versionfile-source` to the same as `versionscript-source`. -->

### Usage (script vendored)

Remember one rule: the `_version.py` file must contain `get_version_dict()` function that returns a dictionary with a "version" key.

```python
# Valid _version.py
def get_version_dict():
    # Your custom logic to get the version string.
    return { "version": version, ... }
```

That means, you can copy-paste the entire `src/version_pioneer/version_pioneer_core.py` to your project, use it as is or customise it to your needs.

```python
# src/version_pioneer/version_pioneer_core.py, pseudo code

class VersionPioneerConfig:
    style: VersionStyle = VersionStyle.pep440
    tag_prefix: str = "v"
    parentdir_prefix: Optional[str] = None
    verbose: bool = False

# ...

def get_version_dict():
    # Run `git describe`, parse the output, and return the version string.
    ...
```

## 🛠️ Configuration

Unlike Versioneer, the configuration is located in two places: `pyproject.toml` and `src/my_project/_version.py`. This is to make it less confusing, because in Versioneer, most of the pyproject.toml config is actually useless once you install `_version.py` in your project.

### pyproject.toml [tool.version-pioneer]: Configuration for build backends and Version-Pioneer CLI. 

- `versionfile-source`: Path to the `_version.py` file in your project, and "sdist" build directory (e.g. `src/my_project/_version.py`)
- `versionfile-build`: Path to the `_version.py` file in "wheel" build directory (e.g. `my_project/_version.py`)

When you build a source distribution (sdist), the `versionfile-source` gets replaced to a short constant file.
When you build a wheel, the `versionfile-build` gets replaced to a short constant file.

> [!NOTE]
> In hatchling backend, `versionfile-build` must be set to the same as `versionfile-source`.
> Their build system is apparently more consistent between the two types.

> [!TIP]
> Leave out the `versionfile-build` setting if you don't want to replace the `_version.py` file in the build directory.
> This applies not only to "wheel" builds but also to "sdist" builds to maintain consistent build results,
> even though "sdist" builds do not actually use the `versionfile-build` setting (they replace the `versionfile-source` file).


The idea is that it just tells you where it is, and the other configs should be parsed directly from `_version.py`.

### `_version.py`: Configuration for resolving the version string.

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


## 💡 Understanding Version-Pioneer (completely vendored, without build backend plugins)

It's important to understand how Version-Pioneer works, so you can customise it to your needs.

### Basic: _version.py as a script

The core functionality is in one file: [`_version.py`](src/version_pioneer/_version.py). This code is either used as a script (`python _version.py`) that prints a json of all useful information, or imported as a module (`from _version import __version__`), depending on your needs. The code looks something like this:

```python
# pseudo code of _version.py, original.
def get_version_dict():
    # Some logic to get the version string from git.
    # Read the source code. You can easily understand and customise it.
    ...

if __name__ == "__main__":
    import json

    print(json.dumps(get_version_dict()))
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
# code to evaluate get_version_dict() from the original _version.py
Path("src/my_project/_version.py").read_text()
module_globals = {}
exec(version_py, module_globals)
print(module_globals["get_version_dict"]())
```

### Basic: building a Python package (replacing _version.py to a constant)

Copy-paste [`src/version_pioneer/_version.py`](src/version_pioneer/_version.py) to your project (like `src/my_project/_version.py`). When you install your package like `pip install -e .`, the code is unchanged, so it will always print up-to-date version string from git tags.

However, if you install like `pip install .` or `pyproject-build`, `uv build` etc., you would lose the git history so the `src/my_project/_version.py` should change.  
The original file is replaced with this. This is generated by literally executing the above file and saving version_dict as a constant.

```python
# pseudo code of _version.py, generated.
def get_version_dict():
    return {
        "version": "0.3.2+15.g2127fd3.dirty",
        "full-revisionid": "2127fd373d14ed5ded497fc18ac1c1b667f93a7d",
        "dirty": True,
        "error": None,
        "date": "2024-12-17T12:25:42+0900",
    }

if __name__ == "__main__":
    import json

    print(json.dumps(get_version_dict()))
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
expression = "get_version_dict()['version']"

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

2. `version-pioneer install` will copy-paste the `_version.py` to the path you specified, and append `__version__` to your `__init__.py`.

If you are using setuptools backend, it will also create a `setup.py` file for you.


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

def get_version_dict():
    return {'version': '0.1.0+8.g6228bc4.dirty', 'full_revisionid': '6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f', 'dirty': True, 'error': None, 'date': '2024-12-21T21:03:48+0900'}


if __name__ == "__main__":
    import json

    print(json.dumps(__version_dict__))
```

### `version-pioneer get-version-builtin`: Get version without using _version.py

This is useful when you want to get the version string without evaluating the `_version.py` file, like your project is probably not Python.

It's the same as running the `version_pioneer_core.py` script, but with more options.

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

## 🚧 Development

Run tests:

```bash
# install uv (brew install uv, pip install uv, ...)
uv pip install deps/requirements-dev.txt
pytest
```

`uv` is required to run tests because we use `uv build`.
