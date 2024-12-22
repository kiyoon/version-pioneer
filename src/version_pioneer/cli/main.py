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

from version_pioneer import VersionStyle
from version_pioneer.api import ResolutionFormat
from version_pioneer.utils.diff import unidiff_output

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
    """Install _version.py at `tool.version-pioneer.versionfile-source` in pyproject.toml."""
    from version_pioneer.api import get_version_py_code
    from version_pioneer.utils.toml import (
        find_pyproject_toml,
        get_toml_value,
        load_toml,
    )

    pyproject_toml_file = find_pyproject_toml(project_dir)
    pyproject_toml = load_toml(pyproject_toml_file)

    project_dir = pyproject_toml_file.parent
    version_py_file = project_dir / Path(
        get_toml_value(
            pyproject_toml, ["tool", "version-pioneer", "versionfile-source"]
        )
    )
    if version_py_file.exists():
        current_version_py_code = version_py_file.read_text()
        package_version_py_code = get_version_py_code()
        if current_version_py_code.strip() == package_version_py_code.strip():
            rich.print(
                f"[green]File already exists:[/green] {version_py_file} (no changes)"
            )
            sys.exit(2)

        unified_diff = unidiff_output(current_version_py_code, package_version_py_code)
        rich.print(Syntax(unified_diff, "diff", line_numbers=True, theme="lightbulb"))
        print()

        confirm = Confirm.ask(
            f"File [green]{version_py_file}[/green] already exists. [red]Overwrite?[/red]",
            default=False,
        )
        if not confirm:
            rich.print("[red]Aborted.[/red]")
            sys.exit(1)

    version_py_file.write_text(get_version_py_code())
    rich.print(f"[green]File written:[/green] {version_py_file}")


@app.command()
def print_orig_version_py_code():
    """Print the content of _version.py file (for manual installation)."""
    from version_pioneer.api import get_version_py_code

    print(get_version_py_code())


@app.command()
def exec_version_py(
    project_dir_or_version_py_file: Annotated[Optional[Path], typer.Argument()] = None,
    output_format: ResolutionFormat = ResolutionFormat.version_string,
):
    """Resolve the _version.py file for build, and print the content."""
    from version_pioneer.api import exec_version_py

    print(exec_version_py(project_dir_or_version_py_file, output_format=output_format))


@app.command()
def get_version_builtin(
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
    WITHOUT using the _version.py file, get version with Version-Pioneer logic.

    Useful when you don't need to customise the _version.py file, and you work in non-Python projects
    so you don't care about re-evaluating the version file.

    Args:
        project_dir: The root or child directory of the project.
        parentdir_prefix: The prefix of the parent directory. (e.g. {github_repo_name}-)
    """
    from version_pioneer.api import get_version_builtin

    print(
        get_version_builtin(
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
