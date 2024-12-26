from __future__ import annotations

import inspect
import json
import logging
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from functools import lru_cache
from importlib.metadata import Distribution, PackageNotFoundError
from os import PathLike
from pathlib import Path

from ._version import get_version_dict as _get_version_dict

__version__ = _get_version_dict()["version"]

logger = logging.getLogger(__name__)

APP_NAME = __name__
APP_NAME_UPPER = APP_NAME.upper()
PACKAGE_NAME = APP_NAME.replace("_", "-")


def setup_logging(
    console_level: int | str = logging.INFO,
    log_dir: str | PathLike | None = None,
    output_files: Sequence[str] = (
        "{date:%Y%m%d-%H%M%S}-{name}-{levelname}-{version}.log",
    ),
    file_levels: Sequence[int] = (logging.INFO,),
    *,
    log_init_messages: bool = True,
    console_formatter: logging.Formatter | None = None,
    file_formatter: logging.Formatter | None = None,
):
    r"""
    Setup logging with RichHandler and FileHandler.

    You should call this function at the beginning of your script.

    Args:
        console_level: Logging level for console. Defaults to INFO or env var {APP_NAME_UPPER}_LOG_LEVEL.
        log_dir: Directory to save log files. If None, only console logging is enabled. Usually set to LOG_DIR.
        output_files: List of output file paths, relative to log_dir. Only applies if log_dir is not None.
        file_levels: List of logging levels for each output file. Only applies if log_dir is not None.
        log_init_messages: Whether to log the initialisation messages.
    """
    try:
        from rich.console import Console
        from rich.logging import RichHandler
        from rich.theme import Theme
    except ModuleNotFoundError:
        print("⚠️ CLI dependencies are not installed.")  # noqa: T201
        print(  # noqa: T201
            "Please install Version-Pioneer with `pip install 'version-pioneer[cli]'`."
        )
        print("or even better, `uv tool install 'version-pioneer[cli]'`.")  # noqa: T201

        sys.exit(1)

    _console = Console(
        theme=Theme(
            {
                "logging.level.error": "bold red blink",
                "logging.level.critical": "red blink",
                "logging.level.warning": "yellow",
                "logging.level.success": "green",
            }
        )
    )

    @lru_cache
    def pkg_is_editable():
        try:
            direct_url = Distribution.from_name(PACKAGE_NAME).read_text(
                "direct_url.json"
            )
        except PackageNotFoundError:
            # Not installed?
            return False

        if direct_url is None:
            # package is not installed at all
            return False
        return json.loads(direct_url).get("dir_info", {}).get("editable", False)

    # NOTE: The value is None if you haven't installed with `pip install -e .` (development mode).
    # We make it None to discourage the use of this path. Only use for development.
    if pkg_is_editable():
        PROJECT_DIR = Path(__file__).parent.parent.parent  # noqa: N806
    else:
        PROJECT_DIR = None  # noqa: N806

    assert len(output_files) == len(
        file_levels
    ), "output_files and file_levels must have the same length"

    if log_dir is None:
        output_files = []
        file_levels = []
    else:
        log_dir = Path(log_dir)

    # NOTE: Initialise with NOTSET level and null device, and add stream handler separately.
    # This way, the root logging level is NOTSET (log all), and we can customise each handler's behaviour.
    # If we set the level during the initialisation, it will affect to ALL streams,
    # so the file stream cannot be more verbose (lower level) than the console stream.
    logging.basicConfig(
        format="",
        level=logging.NOTSET,
        stream=open(os.devnull, "w"),  # noqa: SIM115
    )

    # If you want to suppress logs from other modules, set their level to WARNING or higher
    # logging.getLogger('slowfast.utils.checkpoint').setLevel(logging.WARNING)

    console_handler = RichHandler(
        level=console_level,
        show_time=True,
        show_level=True,
        show_path=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        console=_console,
    )

    if console_formatter is None:
        console_format = logging.Formatter(
            fmt="%(name)s - %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        console_format = console_formatter
    console_handler.setFormatter(console_format)

    if file_formatter is None:
        f_format = logging.Formatter(
            fmt="%(asctime)s - %(name)s: %(lineno)4d - %(levelname)s - %(message)s",
            datefmt="%y/%m/%d %H:%M:%S",
        )
    else:
        f_format = file_formatter

    function_caller_module = inspect.getmodule(inspect.stack()[1][0])
    if function_caller_module is None:
        name_or_path = "unknown"
    elif function_caller_module.__name__ == "__main__":
        if function_caller_module.__file__ is None:
            name_or_path = function_caller_module.__name__
        elif PROJECT_DIR is not None:
            # Called from files in the project directory.
            # Instead of using the __name__ == "__main__", infer the module name from the file path.
            name_or_path = function_caller_module.__file__.replace(
                str(PROJECT_DIR) + "/", ""
            ).replace("/", ".")
            # Remove .py extension
            name_or_path = Path(name_or_path).with_suffix("")
        else:
            # Called from somewhere outside the project directory.
            # Use the script name, like "script.py"
            name_or_path = Path(function_caller_module.__file__).name
    else:
        name_or_path = function_caller_module.__name__

    log_path_map = {
        "name": name_or_path,
        "version": __version__,
        "date": datetime.now(timezone.utc),
    }

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

    if log_init_messages:
        logger.info(f"Running with {PACKAGE_NAME} {__version__}")

    if log_dir is not None:
        log_paths: list[Path] = []
        for output_file, file_level in zip(output_files, file_levels):
            log_path_map["levelname"] = logging._levelToName[file_level]
            log_path = log_dir / output_file.format_map(log_path_map)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_paths.append(log_path)

            f_handler = logging.FileHandler(log_path)
            f_handler.setLevel(file_level)
            f_handler.setFormatter(f_format)

            # Add handlers to the logger
            root_logger.addHandler(f_handler)

        if log_init_messages:
            for log_path in log_paths:
                logger.info(f"Logging to {log_path}")
