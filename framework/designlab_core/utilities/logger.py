"""
designlab_core.utilities.logger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Centralised logger for all DesignLab accelerators.

Usage:
    from designlab_core.utilities.logger import (
        log_info,
        log_warning,
        log_error,
        get_logger,
    )

    log_info(
        "Story generated",
        context={
            "model": "claude-sonnet",
            "tokens": 412,
        }
    )


"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from designlab_core.utilities.env import get_env

# ── Module-level logger ───────────────────────────────────────────────────────

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LevelFilter(logging.Filter):
    """
    Filter that only allows log records within a specific level range (inclusive).
    """
    def __init__(self, low: int, high: int):
        super().__init__()
        self.low = low
        self.high = high

    def filter(self, record: logging.LogRecord) -> bool:
        return self.low <= record.levelno <= self.high


def setup_logging() -> None:
    """
    Initialize the logging system.
    Configures console (sys.stdout) logging and optional file logging with rotation.
    Clears any existing root handlers to prevent duplication.
    """
    env = get_env()

    # Determine console logging level
    console_level = getattr(
        logging,
        env.log_level.upper(),
        logging.INFO,
    )

    # Root level should be set to the lower of console and file levels to capture all logs
    root_level = console_level

    # Define handlers list
    handlers: list[logging.Handler] = []

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)

    # 2. Rotating File Handlers (if configured)
    if env.log_file_path:
        try:
            log_path = Path(env.log_file_path).resolve()
            # Ensure the parent directory exists
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_level = getattr(
                logging,
                env.log_file_level.upper(),
                console_level,
            )

            # Adjust root logger level if file logger needs a lower level (e.g. DEBUG)
            if file_level < root_level:
                root_level = file_level

            # Derive separate info and error file paths
            info_log_path = log_path.parent / f"{log_path.stem}_info{log_path.suffix}"
            error_log_path = log_path.parent / f"{log_path.stem}_error{log_path.suffix}"

            # Use a more detailed trace log format for files
            file_format = "%(asctime)s [%(levelname)s] [%(process)d:%(threadName)s] %(name)s (%(filename)s:%(lineno)d) — %(message)s"
            file_formatter = logging.Formatter(fmt=file_format, datefmt=_DATE_FORMAT)

            # A. Info/Warning Handler (DEBUG to WARNING)
            info_handler = RotatingFileHandler(
                filename=info_log_path,
                maxBytes=env.log_file_max_bytes,
                backupCount=env.log_file_backup_count,
                encoding="utf-8",
            )
            info_handler.setLevel(file_level)
            info_handler.setFormatter(file_formatter)
            info_handler.addFilter(LevelFilter(logging.DEBUG, logging.WARNING))
            handlers.append(info_handler)

            # B. Error Handler (ERROR to CRITICAL)
            error_handler = RotatingFileHandler(
                filename=error_log_path,
                maxBytes=env.log_file_max_bytes,
                backupCount=env.log_file_backup_count,
                encoding="utf-8",
            )
            # Make sure error handler writes at least ERROR logs
            error_handler_level = max(file_level, logging.ERROR)
            error_handler.setLevel(error_handler_level)
            error_handler.setFormatter(file_formatter)
            error_handler.addFilter(LevelFilter(logging.ERROR, logging.CRITICAL))
            handlers.append(error_handler)

        except Exception as e:
            # Fall back gracefully if logging file cannot be created (e.g., due to permissions)
            print(
                f"Warning: Failed to initialize file loggers at {env.log_file_path} ({e}). "
                f"Falling back to console-only logging.",
                file=sys.stderr,
            )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)

    # Clear existing handlers to prevent duplicate messages in hot-reload or test suites
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Add configured handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)


# Auto-configure logging upon import
setup_logging()

_logger = logging.getLogger("designlab")


def _format_context(context: dict[str, Any] | None = None) -> str:
    """
    Convert context dictionary into a log-friendly string.

    Example:
        {"model": "claude", "tokens": 412}
        ->
        " | model=claude tokens=412"
    """
    if not context:
        return ""

    return " | " + " ".join(
        f"{key}={value}"
        for key, value in context.items()
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named child logger.

    Example:
        logger = get_logger(__name__)
        logger.info("Story generation started")
    """
    return logging.getLogger(f"designlab.{name}")


def log_info(
    message: str,
    context: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    """
    Log an informational message.

    Supports both:
        log_info("msg", context={"model": "claude"})
    and
        log_info("msg", model="claude")
    """
    merged_context = dict(context or {})

    if extra:
        merged_context.update(extra)

    _logger.info(
        message + _format_context(merged_context),
        stacklevel=2,
    )


def log_warning(
    message: str,
    context: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    """
    Log a warning message.
    """
    merged_context = dict(context or {})

    if extra:
        merged_context.update(extra)

    _logger.warning(
        message + _format_context(merged_context),
        stacklevel=2,
    )


def log_error(
    message: str,
    exc: Exception | None = None,
    context: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    """
    Log an error message.

    Supports both:
        log_error("failed", context={"model": "claude"})
    and
        log_error("failed", model="claude")
    """
    merged_context = dict(context or {})

    if extra:
        merged_context.update(extra)

    _logger.error(
        message + _format_context(merged_context),
        exc_info=exc is not None,
        stacklevel=2,
    )