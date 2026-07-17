"""Structured logging on top of loguru.

Usage::

    from ogip.logger import logger, setup_logging

    setup_logging(level="INFO", json_logs=False)
    logger.bind(source="rawg", entity="games").info("extracted {n} rows", n=42)

Flows bind run context (``flow_run_id``, ``source``, ``entity``) so every line is
attributable; the JSON sink (``json_logs=True`` / ``OGIP_LOG_JSON``) carries bound
context in the ``extra`` payload for Loki aggregation.
"""

import sys
from pathlib import Path

from loguru import logger

__all__ = ["logger", "setup_logging"]

_HUMAN_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
    "<level>{message}</level>"
)


def setup_logging(
    *, level: str = "INFO", json_logs: bool = False, log_file: Path | None = None
) -> None:
    """Configure the global logger. Idempotent — replaces all existing sinks.

    When ``log_file`` is given (canonical: ``.run/logs/ogip.log`` — never the repo
    root), a rotating file sink is added alongside stderr.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        format="{message}" if json_logs else _HUMAN_FORMAT,
        serialize=json_logs,
        backtrace=False,
        diagnose=False,
    )
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=level.upper(),
            serialize=json_logs,
            rotation="10 MB",
            retention="14 days",
            backtrace=False,
            diagnose=False,
        )
