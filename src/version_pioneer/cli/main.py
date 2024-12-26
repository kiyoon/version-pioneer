# Allow print
# Allow many arguments
# Allow relative import from parent
# Allow using Optional
# ruff: noqa: T201 PLR0913 TID252 FA100

# NOTE: type | None only works in Python 3.10+ with typer, so we use Optional instead.

import sys

try:
    import rich
    import typer
    from rich.prompt import Confirm
    from rich.syntax import Syntax

    from .docstring import from_docstring
except ModuleNotFoundError:
    print("⚠️ CLI dependencies are not installed.")
    print("Please install Version-Pioneer with `pip install 'version-pioneer[cli]'`.")
    print("or even better, `uv tool install 'version-pioneer[cli]'`.")

    sys.exit(1)


from pathlib import Path
from typing import List, Optional

from version_pioneer.template import INIT_PY, NO_VENDOR_VERSIONSCRIPT, SETUP_PY
from version_pioneer.utils.diff import unidiff_output
from version_pioneer.utils.version_script import ResolutionFormat
from version_pioneer.versionscript import VersionStyle

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

app = typer.Typer(
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="🧗 Version-Pioneer: Dynamically manage project version with hatchling and pdm support.",
)


def version_callback(*, value: bool):
    if value:
        from .. import __version__

        print(__version__)
        raise typer.Exit


@app.callback()
def common(
    ctx: typer.Context,
    *,
    version: bool = typer.Option(
        None, "-v", "--version", callback=version_callback, help="Show version"
    ),
):
    pass


@app.command()
@from_docstring
def install(
    project_dir: Annotated[Optional[Path], typer.Argument()] = None,
    *,
    vendor: bool = True,
):
    """
    Add _version.py, modify __init__.py and maybe setup.py.

    Args:
        project_dir: The root or child directory of the project. Default is cwd.
        vendor: Install the full versionscript. --no-vendor to import from version_pioneer.
    """
    from version_pioneer.api import get_version_script_core_code
    from version_pioneer.utils.toml import (
        find_pyproject_toml,
        get_toml_value,
        load_toml,
    )

    def _write_file_with_diff_confirm(file: Path, content: str):
        if file.exists():
            existing_content = file.read_text()
            if existing_content.strip() == content.strip():
                rich.print(f"[green]File already exists:[/green] {file} (no changes)")
                sys.exit(2)

            unified_diff = unidiff_output(existing_content, content)
            rich.print(
                Syntax(unified_diff, "diff", line_numbers=True, theme="lightbulb")
            )
            print()

            confirm = Confirm.ask(
                f"File [green]{file}[/green] already exists. [red]Overwrite?[/red]",
                default=False,
            )
            if not confirm:
                rich.print("[red]Aborted.[/red]")
                sys.exit(1)

        file.write_text(content)
        rich.print(f"[green]File written:[/green] {file}")

    pyproject_toml_file = find_pyproject_toml(project_dir)
    pyproject_toml = load_toml(pyproject_toml_file)

    project_dir = pyproject_toml_file.parent
    version_script_file = project_dir / Path(
        get_toml_value(
            pyproject_toml,
            ["tool", "version-pioneer", "versionscript"],
            raise_error=True,
        )
    )

    if vendor:
        _write_file_with_diff_confirm(
            version_script_file, get_version_script_core_code()
        )
    else:
        _write_file_with_diff_confirm(version_script_file, NO_VENDOR_VERSIONSCRIPT)

    # Modify __init__.py
    init_py_file = version_script_file.parent / "__init__.py"
    if not init_py_file.exists():
        init_py_file.write_text(INIT_PY)
        rich.print(f"[green]{init_py_file} added with content:[/green]")
        print(INIT_PY)
    else:
        init_py_content = init_py_file.read_text()
        init_py_template_lines = [line for line in INIT_PY.splitlines() if line.strip()]
        # if all lines exists in the init_py_content
        if all(line in init_py_content for line in init_py_template_lines):
            print("__init__.py already configured. Not modifying.")
        else:
            init_py_file.write_text(INIT_PY + "\n\n" + init_py_content)
            rich.print(f"[green]{init_py_file} modified with[/green]")
            print(INIT_PY)
            rich.print("[green]at the top![/green]")

    # Using setuptools.build_meta backend?
    try:
        build_backend = get_toml_value(
            pyproject_toml, ["build-system", "build-backend"], raise_error=True
        )
    except KeyError:
        confirm = Confirm.ask(
            "Are you using setuptools.build_meta backend? Install setup.py?",
            default=False,
        )

        if confirm:
            build_backend = "setuptools.build_meta"
        else:
            build_backend = None

    if build_backend is not None and build_backend == "setuptools.build_meta":
        # install setup.py
        setup_py_file = project_dir / "setup.py"
        _write_file_with_diff_confirm(setup_py_file, SETUP_PY)

    rich.print("[green]Installation completed![/green]")


@app.command()
def print_versionscript_code():
    """Print the content of versionscript.py file (for manual installation)."""
    from version_pioneer.api import get_version_script_core_code

    print(get_version_script_core_code())


@app.command()
def exec_version_script(
    project_dir_or_version_script_file: Annotated[
        Optional[Path], typer.Argument()
    ] = None,
    output_format: ResolutionFormat = ResolutionFormat.version_string,
):
    """Resolve the _version.py file for build, and print the content."""
    from version_pioneer.api import exec_version_script_and_convert

    print(
        exec_version_script_and_convert(
            project_dir_or_version_script_file, output_format=output_format
        )
    )


@app.command()
@from_docstring
def get_version_wo_exec(
    project_dir: Annotated[Optional[Path], typer.Argument()] = None,
    *,
    style: VersionStyle = VersionStyle.pep440,
    tag_prefix: str = "v",
    parentdir_prefix: Optional[str] = None,
    output_format: ResolutionFormat = ResolutionFormat.version_string,
    verbose: bool = False,
):
    """
    WITHOUT evaluating the _version.py file, get version from VCS with built-in Version-Pioneer logic.

    Useful when you don't need to customise the _version.py file, and you work in non-Python projects
    so you don't care about re-evaluating the version file.

    Args:
        project_dir: The root or child directory of the project. Default is cwd.
        parentdir_prefix: The prefix of the parent directory. (e.g. {github_repo_name}-)
    """
    from version_pioneer.api import get_version_wo_exec_and_convert

    print(
        get_version_wo_exec_and_convert(
            project_dir,
            style=style,
            tag_prefix=tag_prefix,
            parentdir_prefix=parentdir_prefix,
            output_format=output_format,
            verbose=verbose,
        )
    )


@app.command()
@from_docstring
def build_consistency_test(
    project_dir: Annotated[Optional[Path], typer.Argument()] = None,
    *,
    delete_temp_dir: bool = True,
    expected_version: Optional[str] = None,
    test_chaining: bool = True,
    ignore_patterns: Annotated[List[str], typer.Option("--ignore-pattern", "-i")] = [  # noqa: B006
        "*.egg-info/SOURCES.txt"
    ],
):
    """
    Check if builds are consistent with sdist, wheel, both, sdist -> sdist.

    Args:
        project_dir: The root or child directory of the project. Default is cwd.
        expected_version: Check if it builds to the expected version (without tag prefix).
        ignore_patterns: List of patterns to ignore when seeing diff of directory.
        test_chaining: Test sdist -> sdist chaining.
            Note that some build backends may produce different results.
            For example, setuptools produces setup.cfg in the first build,
            so the second result will have one more file in the SOURCES.txt list.
    """
    from version_pioneer import setup_logging
    from version_pioneer.api import build_consistency_test

    setup_logging()
    build_consistency_test(
        project_dir,
        delete_temp_dir=delete_temp_dir,
        test_chaining=test_chaining,
        expected_version=expected_version,
        ignore_patterns=ignore_patterns,
    )


def main():
    app()


if __name__ == "__main__":
    main()
