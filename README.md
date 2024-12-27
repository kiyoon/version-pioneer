# 🧗🏽 Version-Pioneer: General-Purpose Versioneer for Any Build Backends

[![image](https://img.shields.io/pypi/v/version-pioneer.svg)](https://pypi.python.org/pypi/version-pioneer)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/version-pioneer)](https://pypistats.org/packages/version-pioneer)
[![image](https://img.shields.io/pypi/l/version-pioneer.svg)](https://pypi.python.org/pypi/version-pioneer)
[![image](https://img.shields.io/pypi/pyversions/version-pioneer.svg)](https://pypi.python.org/pypi/version-pioneer)

|  |  |
|--|--|
|[![Ruff](https://img.shields.io/badge/Ruff-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/astral-sh/ruff) |[![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Style%20checking/badge.svg)](https://github.com/kiyoon/version-pioneer/actions)|
| [![Ruff](https://img.shields.io/badge/Ruff-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/astral-sh/ruff) | [![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Linting/badge.svg)](https://github.com/kiyoon/version-pioneer/actions) |
| [![pytest](https://img.shields.io/badge/pytest-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/pytest-dev/pytest) [![doctest](https://img.shields.io/badge/doctest-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://docs.python.org/3/library/doctest.html) | [![Actions status](https://github.com/kiyoon/version-pioneer/workflows/Tests/badge.svg)](https://github.com/kiyoon/version-pioneer/actions) [![codecov](https://codecov.io/gh/kiyoon/version-pioneer/graph/badge.svg?token=QS5JX9VTPM)](https://codecov.io/gh/kiyoon/version-pioneer) |
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

- 🧑‍🍳 **Highly customisable**: It's an easy-to-read script. Literally a simple python script which you can customise version format or anything as you need.
- 🐍 Runs with Python 3.8+
- ❌📦 No dependencies like package, config file etc. It runs with one python file. 
- ⭕ Works with any build backend with hooks.
- 🦀 Works with any language, not just Python.
    - Support for new version formats like `"digits"` that generates digits-only version string like `1.2.3.4` instead of `1.2.3+4.gxxxxxxx`. Useful for multi-language projects, Chrome Extension, etc. because their versioning standard is different.
- 🩹 Can resolve version even when the git info is missing.
    - Downloaded from GitHub Releases? Read from the directory name.
        - The `parentdir_prefix` is automatically resolved from `pyproject.toml`'s source URL etc.
    - sdist built without writing a resolved versionfile?
        - Read from PKG-INFO. 
- 🔢 New version formats like `"pep440-master"` that shows the distance from the tag to master/main, and the master to the current branch.
- </> API provided for complete non-vendored mode support.
    - With Versioneer you still had to install a `_version.py` script in your project, but Version-Pioneer is able to be installed as a package.
- 💻 CLI tool to get version string, execute the `_version.py` versionscript, and test your setup.


## 🏃 Quick Start (script not vendored, with build backend plugins)

1. Configure `pyproject.toml`. `[tool.version-pioneer]` section is required.
    ```toml
    [tool.version-pioneer]
    versionscript = "src/my_project/_version.py"  # Where to "read" the Version-Pioneer script (to execute `get_version_dict()`).
    versionfile-sdist = "src/my_project/_version.py"  # Where to "write" the version dict for sdist.
    versionfile-wheel = "my_project/_version.py"  # Where to "write" the version dict for wheel.
    ```

2. Create `src/my_project/_version.py` with `get_version_dict()` in your project.
    ```python
    # Example _version.py, completely non-vendored.
    from pathlib import Path

    from version_pioneer.api import get_version_dict_wo_exec


    def get_version_dict():
        # NOTE: during installation, __file__ is not defined
        # When installed in editable mode, __file__ is defined
        # When installed in standard mode (when built), this file is replaced to a compiled versionfile.
        if "__file__" in globals():
            cwd = Path(__file__).parent
        else:
            cwd = Path.cwd()

        return get_version_dict_wo_exec(
            cwd=cwd,
            style="pep440",
            tag_prefix="v",
        )
    ```

3. Put the following code in your project's `__init__.py` to use the version string.
    ```python
    # src/my_project/__init__.py
    from ._version import get_version_dict

    __version__ = get_version_dict()["version"]
    ```

> [!TIP]
> Use `version-pioneer install --no-vendor` CLI command to perform the step 2 and 3 automatically.

4. Configure your build backend to execute `_version.py` and use the version string. Setuptools, Hatchling and PDM are supported.

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
source = "version-pioneer"

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

Voilà! The version string is now dynamically generated from git tags, and the `_version.py` file is replaced with a constant "versionfile" when building a wheel or source distribution.

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


### Usage with vendoring the script

If you don't want to add a dev dependency, you can simply vendor the "versionscript" in your project.

Copy-paste the entire [`versionscript.py`](src/version_pioneer/versionscript.py) to your project, use it as is or customise it to your needs.

If you choose to modify the script, remember one rule: the versionscript file must contain `get_version_dict()` function that returns a dictionary with a "version" key. (more precisely, the `VersionDict` type in the script.)

```python
# Valid _version.py
def get_version_dict():
    # Your custom logic to get the version string.
    return { "version": version, ... }
```

> [!TIP]
> Use `version-pioneer install` or `version-pioneer print-versionscript-code` CLI commands that helps you install (vendor) the `versionscript.py` file to your project.


## 🛠️ Configuration

Unlike Versioneer, the configuration is located in two places: `pyproject.toml` and the "versionscript" (`src/my_project/_version.py`). This is to make it less confusing, because in Versioneer, most of the pyproject.toml config were actually useless once you install `versionscript.py` in your project.

The idea is that the toml config just tells you where the script is (for build backends to identify them), and the script has everything it needs. 

### `pyproject.toml` [tool.version-pioneer]: Configuration for build backends and Version-Pioneer CLI. 

- `versionscript`: Path to the versionscript to execute `get_version_dict()`. (e.g. `src/my_project/_version.py`)
- `versionfile-sdist`: Path to save the resolved versionfile in the *sdist* build directory (e.g. `src/my_project/_version.py`)
- `versionfile-wheel`: Path to save the resolved versionfile in the *wheel* build directory (e.g. `my_project/_version.py`)

The main idea is that when you build your project, "versionscript" is executed to write the "versionfile".  
When you build a source distribution (sdist), the `versionfile-sdist` gets replaced to a short constant file.  
When you build a wheel, the `versionfile-wheel` gets replaced to a short constant file.

> [!TIP]
> Leave out the `versionfile-sdist` and/or `versionfile-wheel` setting if you don't want to write/replace the versionfile in the build directory. 


### `_version.py` versionscript: Configuration for resolving the version string.

You can modify the config in the script. 

```python
@dataclass(frozen=True)
class VersionPioneerConfig:
    style: VersionStyle = VersionStyle.pep440
    tag_prefix: str = "v"
    parentdir_prefix: Optional[str] = None
    verbose: bool = False
```

- `style`: similar to Versioneer's `style` option. Three major styles are:
    - `pep440`: "1.2.3+4.gxxxxxxx.dirty" (default)
    - `pep440-master`: "1.2.3+4.gxxxxxxx.5.gxxxxxxx.dirty"
        - Shows the distance from the tag to master/main, and the master to the current branch.
        - Useful when you mainly work on a branch and merge to master/main.
    - `digits`: "1.2.3.5"
        - Digits-only version string.
        - The last number is the distance from the tag (dirty is counted as 1, thus 5 in this example).
        - Useful for multi-language projects, Chrome Extension, etc.
    - See Versioneer for more styles (or read documentation in _version.py).
- `tag_prefix`: tag to look for in git for the reference version.
- `parentdir_prefix`: if there is no .git, like it's a source tarball downloaded from GitHub Releases, find version from the name of the parent directory. e.g. setting it to "github-repo-name-" will find the version from "github-repo-name-1.2.3"
    - 🔍 Set to None to automatically inferred from pyproject.toml's GitHub/GitLab URL or project name. (New in Version-Pioneer)
- `verbose`: print debug messages.

If you want to customise the logic, you can modify the entire script. However you modify the script, remember that this file has to be able to run like a standalone script without any other dependencies (like package, files, config, etc.).

## 💡 Understanding Version-Pioneer (completely vendored, without build backend plugins)

This section explains how Version-Pioneer works, so you can customise it to your needs.

### Basic: versionscript.py as a script

The core functionality is in one file: [`versionscript.py`](src/version_pioneer/versionscript.py). This code is either used as a script (`python versionscript.py`) that prints a json of all useful information, or imported as a module (`from my_project.versionscript import get_version_dict`), depending on your needs.

Run it in your project to see what it prints. Change git tags, commit, and see how it changes.

```console
$ git tag v1.2.3
$ python versionscript.py
{"version": "1.2.3", "full_revisionid": "xxxxxx", "dirty": False, "error": None, "date": "2024-12-17T12:25:42+0900"}
$ git commit --allow-empty -m "commit"
$ python versionscript.py
{"version": "1.2.3+1.gxxxxxxx", "full_revisionid": "xxxxxx", "dirty": True, "error": None, "date": "2024-12-17T12:25:42+0900"}
```

### Basic: converting versionscript.py to a constant versionfile (for build)

You lose the git history during build, so you need to convert the `versionscript.py` to a constant version string.  
Just `exec` the original `versionscript.py` and save the result as you wish: text, json, etc.

```python
# code to evaluate get_version_dict() from the version script
Path("src/my_project/_version.py").read_text()
module_globals = {}
exec(version_py, module_globals)
print(module_globals["get_version_dict"]())
```

### Basic: building a Python package (replacing "versionscript" to a constant "versionfile")

Place `versionscript.py` in your project source directory (like `src/my_project/_version.py`). When you install your package like `pip install -e .`, the code is unchanged, so it will always print up-to-date version string from git tags.

However, if you install like `pip install .` or `pyproject-build`, `uv build` etc., you would lose the git history so the `src/my_project/_version.py` should change.  
The original file is replaced with this. This is generated by literally executing the above file and saving version_dict as a constant.

```python
# pseudo code of _version.py "versionfile", generated.
def get_version_dict():
    return { "version": "0.3.2+15.g2127fd3.dirty", "full_revisionid": "2127fd373d14ed5ded497fc18ac1c1b667f93a7d", "dirty": True, "error": None, "date": "2024-12-17T12:25:42+0900" }
```

### Advanced: Configuring a 🥚 Hatchling Hook

Even if you are not familiar with Hatchling, hear me out. It is very straightforward.

Add hatchling configuration to `pyproject.toml`.

> [!NOTE]
> In this tutorial, we're assuming that `versionscript` == `versionfile-sdist` for the sake of simplicity.
> This will replace the _version.py itself.
>
> If you want to keep the original versionscript.py (different `versionfile-sdist`), first exec `versionfile-sdist` if it exists, otherwise exec `versionscript`.  
> The reason is that once sdist is built, the version should have been already evaluated and the git information is removed, so `versionfile-sdist` must take precedence.

```toml
[build-system]
requires = ["hatchling", "tomli ; python_version < '3.11'"]
build-backend = "hatchling.build"

# We assume versionscript == versionfile-sdist thus we can use what hatchling provides, and we don't need a metadata hook.
[tool.hatch.version]
source = "code"
path = "src/my_project/_version.py"
expression = "get_version_dict()['version']"

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"

[tool.version-pioneer]
versionscript = "src/my_project/_version.py"
versionfile-sdist = "src/my_project/_version.py"
versionfile-wheel = "my_project/_version.py"

[project]
name = "my-project"
dynamic = ["version"]
```

Add `hatch_build.py` to the project root.

```python
from __future__ import annotations

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

        # evaluate the original versionscript.py file to get the computed versionfile
        versionscript = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionscript"]
        )
        version_py = versionscript.read_text()
        module_globals = {}
        exec(version_py, module_globals)
        version_dict = module_globals["get_version_dict"]()

        # replace the file with the constant version
        self.temp_version_file = tempfile.NamedTemporaryFile(mode="w", delete=True)  # noqa: SIM115
        self.temp_version_file.write(
            textwrap.dedent(f"""
                # THIS "versionfile" IS GENERATED BY version-pioneer
                # by evaluating the original versionscript and storing the computed versions as a constant.

                def get_version_dict():
                    return {version_dict}
            """).strip()
        )
        self.temp_version_file.flush()

        build_data["force_include"][self.temp_version_file.name] = Path(
            pyproject_toml["tool"]["version-pioneer"]["versionfile-sdist"]
        )
```

It just replaces the `_version.py` "versionscript" with a constant "versionfile", by executing the versionscript.
This is skipped when the project is installed in editable mode (`pip install -e .`).

Now you can install your package with `pip install .`, `pip install -e .`, or build a wheel with `hatch build`, `pyproject-build` (`python -m build`), or `uv build`.

> [!IMPORTANT]
> Validate if `uv build --sdist`, `uv build --wheel` produces the same result as `uv build` (both sdist and wheel are built at the same time).
> We provide a CLI command `version-pioneer build-consistency-test` to help you with this.

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
versionscript = "src/my_project/_version.py"
versionfile-sdist = "src/my_project/_version.py"
versionfile-wheel = "my_project/_version.py"

[project]
name = "my-project"
dynamic = ["version"]
```

🐍 pdm_build.py:

```python
import textwrap
from pathlib import Path

from pdm.backend.hooks.base import Context


def pdm_build_initialize(context: Context):
    # Update metadata version
    versionscript = Path(
        context.config.data["tool"]["version-pioneer"]["versionscript"]
    )
    versionscript_code = versionscript.read_text()
    version_module_globals = {}
    exec(versionscript_code, version_module_globals)
    version_dict = version_module_globals["get_version_dict"]()
    context.config.metadata["version"] = version_dict["version"]

    # Write the static version file
    if context.target != "editable":
        if context.target == "wheel":
            versionscript = context.config.data["tool"]["version-pioneer"][
                "versionfile-wheel"
            ]

        context.ensure_build_dir()
        versionscript = context.build_dir / Path(versionscript)
        versionscript.parent.mkdir(parents=True, exist_ok=True)
        versionscript.write_text(
            textwrap.dedent(f"""
                # THIS "versionfile" IS GENERATED BY version-pioneer
                # by evaluating the original versionscript and storing the computed versions as a constant.

                def get_version_dict():
                    return {version_dict}
            """).strip()
        )
```

## 🚀 Version-Pioneer CLI

The above usage should be completely fine, but we also provide a CLI tool to help you install and evaluate versionscript.py.

```bash
# Install with pip
pip install 'version-pioneer[cli]'

# Install with uv tool (in a separate environment, just for the CLI)
uv tool install 'version-pioneer[cli]'
```

```console
$ version-pioneer

 Usage: version-pioneer [OPTIONS] COMMAND [ARGS]...

 🧗 Version-Pioneer: Dynamically manage project version with hatchling and pdm support.

╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ install                    Add _version.py, modify __init__.py and maybe setup.py.                                             │
│ print-versionscript-code   Print the content of _version.py (versionscript.py) file (for manual installation).                 │
│ exec-version-script        Resolve the _version.py file for build, and print the content.                                      │
│ get-version-wo-exec        WITHOUT evaluating the _version.py file, get version from VCS with built-in Version-Pioneer logic.  │
│ build-consistency-test     Check if builds are consistent with sdist, wheel, both, sdist -> sdist.                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


### `version-pioneer install`: Install _version.py to your project

1. Configure `pyproject.toml` with `[tool.version-pioneer]` section.

```toml
[tool.version-pioneer]
versionscript = "src/my_project/_version.py"
versionfile-sdist = "src/my_project/_version.py"
versionfile-wheel = "my_project/_version.py"
```

2. `version-pioneer install` will copy-paste the [`versionscript.py`](src/version_pioneer/versionscript.py) to the `versionscript` path you specified, and define `__version__` to your `__init__.py`.

If you are using setuptools backend, it will also create a `setup.py` file for you.

You can set `--no-vendor` option to import `version_pioneer` as a module to reduce the boilerplate code in your project. (This adds a dev dependency to your project.)


### `version-pioneer exec-version-script`: Resolve _version.py and get the version

Examples:

```console
$ version-pioneer exec-version-script --output-format version-string
0.1.0+8.g6228bc4.dirty

$ version-pioneer exec-version-script --output-format json
{"version": "0.1.0+8.g6228bc4.dirty", "full_revisionid": "6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f", "dirty": true, "error": null, "date": "2024-12-21T21:03:48+0900"}

$ version-pioneer exec-version-script --output-format python
#!/usr/bin/env python3
# THIS "versionfile" IS GENERATED BY version-pioneer-0.1.0
# by evaluating the original versionscript and storing the computed versions as a constant.

def get_version_dict():
    return {'version': '0.1.0+8.g6228bc4.dirty', 'full_revisionid': '6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f', 'dirty': True, 'error': None, 'date': '2024-12-21T21:03:48+0900'}


if __name__ == "__main__":
    import json

    print(json.dumps(__version_dict__))
```

### `version-pioneer get-version-wo-exec`: Get version without using _version.py

This is useful when you want to get the version string without evaluating the versionscript file, like your project is probably not Python.

It's the same as running the `versionscript.py` script (unchanged, not the vendored one), but with more options.

```console
$ version-pioneer get-version-wo-exec
0.1.0+8.g6228bc4.dirty

$ version-pioneer get-version-wo-exec --output-format json
{"version": "0.1.0+8.g6228bc4.dirty", "full_revisionid": "6228bc46e14cfc4e238e652e56ccbf3f2cb1e91f", "dirty": true, "error": null, "date": "2024-12-21T21:03:48+0900"}

$ version-pioneer get-version-wo-exec --style digits
0.1.0.9
```

### `version-pioneer build-consistency-test`: Test build consistency

Useful to check if you have configured Version-Pioneer correctly. It builds the project with `uv build`, `uv build --sdist`, `uv build --wheel`, and checks if the version strings and the package content are consistent. Also it builds sdist from sdist and perform the check.

```console
$ version-pioneer build-consistency-test
06:35:25 INFO     version_pioneer - Running with version-pioneer 0.1.0+41.g8b148ed.dirty               __init__.py:202
         INFO     version_pioneer.api - Testing build consistency...                                        api.py:212
         INFO     version_pioneer.api - Changing cwd to /Users/kiyoon/project/version-pioneer               api.py:220
         INFO     version_pioneer.api - Building the project with `uv build`                                api.py:226
06:35:26 INFO     version_pioneer.api - Building the project with `uv build --sdist` and `uv build --wheel` api.py:235
06:35:27 SUCCESS  version_pioneer.api - ✅ 2 wheel builds are consistent.                                   api.py:272
         SUCCESS  version_pioneer.api - ✅ 2 sdist builds are consistent.                                   api.py:288
         INFO     version_pioneer.api - Building the project with `uv build --sdist` using the built sdist  api.py:290
                  (chaining test).
         INFO     version_pioneer.api - Changing cwd to the built sdist directory:                          api.py:294
                  /var/folders/r5/9cpfjfjx3b73b6stl7_w712h0000gn/T/tmpzuq_uwdn/dist/version_pioneer-0.1.0+4
                  1.g8b148ed.dirty
         SUCCESS  version_pioneer.api - ✅ Chained sdist builds are consistent.                             api.py:324
         INFO     version_pioneer.api - Build wheel using the sdist.                                        api.py:327
06:35:28 SUCCESS  version_pioneer.api - ✅ sdist -> wheel chained build is consistent with the non-chained  api.py:346
                  build.
         INFO     version_pioneer.api - Deleting temporary directory                                        api.py:351
                  /var/folders/r5/9cpfjfjx3b73b6stl7_w712h0000gn/T/tmpzuq_uwdn
         SUCCESS  version_pioneer.api - 💓 All tests passed! 3 sdist builds and 3 wheel builds are          api.py:354
                  consistent.


```


## 📚 Note

- Only supports git.
- `git archive` is not supported. Original Versioneer uses `.gitattributes` to tell git to replace some strings in `_version.py` when archiving. But this is not enough information (at least in my case) and the version string always becomes `0+unknown`. So I dropped it.


### Build chaining problem

It's good to note that, chaining building (project -> sdist -> sdist -> wheel) may result in different version strings if not configured correctly. We take the following strategy to make it consistent:

1. `versionfile-sdist` is evaluated first, if it exists.

Most of the time your `versionscript` and `versionfile-sdist` would be the same. But for some reason you choose to have a seaparate file,
and imagine if we execute the versionscript again in a built sdist. It may produce a different version string because now we don't have git information.

Therefore, `versionfile-sdist` takes precedence (if it exists) over `versionscript`, for resolving version.


2. Each backend works differently under the hood. Some things to note:

**Setuptools**:

- If `setup.cfg` doesn't exist, the sdist build will generate the file.
    - Thus, if you build sdist from sdist, the `*.egg-info/SOURCES.txt` will contain `setup.cfg` so the result is slightly different.
- `version_pioneer.build.setuptools.get_version()` finds the PKG-INFO to look up the version.
    - It's the function you used in `setup(version=get_version())`.
    - Building from sdist wouldn't look at git tags, but the `PKG-INFO` file. So the version string is consistent after multiple builds.

**Hatchling**:

- Once sdist is built, the PKG-INFO is present, and hatchling's version source plugin is ignored.
- `versionfile-wheel` doesn't really get used, but I would still configure it for consistency.

**PDM Backend**:

- Building with pdm removes `dynamic = ["version"]` from `pyproject.toml`'s `[project]` section.
    - Instead, the `version="0.1.0"` (whatever it is during the build) is written.
- However, the build hook can still change the metadata version, thus the versionfile / versionscript is still executed.
    - It will be the versionfile that is already resolved, so the version string is consistent.

## 🚧 Development

Run tests:

```bash
# install uv (brew install uv, pip install uv, ...)
uv pip install deps/requirements-dev.in
pytest
```

`uv` is required to run tests because we use `uv build`.

Types of tests:

- install with setuptools, hatchling, pdm
- version after tag, commit, dirty
- invalid version-pioneer config
- build with `uv build`, `uv build --sdist`, `uv build --wheel`
    - Important: all three can produce different results if sdist isn't generated correctly from the first place.
    - When building both at the same time (`uv build`), it seems to make sdist first and then wheel from the sdist (not directly from the source dir).
    - If the sdist doesn't contain resolved `_version.py`, the wheel build will get no version, because git information is gone.
