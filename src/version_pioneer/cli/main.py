# Allow print
# Allow many arguments
# Allow relative import from parent
# Allow using Optional
# ruff: noqa: T201 PLR0913 TID252 FA100

# NOTE: type | None only works in Python 3.10+ with typer, so we use Optional instead.

try:
    import typer
except ModuleNotFoundError:
    print("⚠️ CLI dependencies are not installed.")
    print("Please install Version-Pioneer with `pip install 'version-pioneer[cli]'`.")
    print("or even better, `uv tool install version-pioneer[cli]`.")
    import sys

    sys.exit(1)


import sys
from pathlib import Path
from typing import Optional

import rich
from rich.prompt import Confirm
from rich.syntax import Syntax

from version_pioneer.template import INIT_PY, SETUP_PY
from version_pioneer.utils.diff import unidiff_output
from version_pioneer.utils.version_script import ResolutionFormat
from version_pioneer.version_pioneer_core import VersionStyle

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
def install(project_dir: Annotated[Optional[Path], typer.Argument()] = None):
    """Add _version.py, modify __init__.py and maybe setup.py."""
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

    _write_file_with_diff_confirm(version_script_file, get_version_script_core_code())

    # Modify __init__.py
    init_py_file = version_script_file.parent / "__init__.py"
    if not init_py_file.exists():
        init_py_file.write_text(INIT_PY)
        rich.print(f"[green]{init_py_file} added with content:[/green]")
        print(INIT_PY)
    else:
        init_py_content = init_py_file.read_text()
        if INIT_PY not in init_py_content:
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
def print_version_script_code():
    """Print the content of _version.py file (for manual installation)."""
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
def get_version(
    project_dir: Annotated[
        Optional[Path], typer.Argument(help="Git directory. Default is cwd")
    ] = None,
    *,
    style: VersionStyle = VersionStyle.pep440,
    tag_prefix: str = "v",
    parentdir_prefix: Optional[str] = None,
    output_format: ResolutionFormat = ResolutionFormat.version_string,
):
    """
    WITHOUT evaluating the _version.py file, get version from VCS with built-in Version-Pioneer logic.

    Useful when you don't need to customise the _version.py file, and you work in non-Python projects
    so you don't care about re-evaluating the version file.

    Args:
        project_dir: The root or child directory of the project.
        parentdir_prefix: The prefix of the parent directory. (e.g. {github_repo_name}-)
    """
    from version_pioneer.api import get_version

    print(
        get_version(
            project_dir,
            style=style,
            tag_prefix=tag_prefix,
            parentdir_prefix=parentdir_prefix,
            output_format=output_format,
        )
    )


def main():
    app()


if __name__ == "__main__":
    main()
