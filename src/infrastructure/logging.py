from __future__ import annotations

import logging
import sys
from typing import Literal

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_format: Literal["json", "console"] = "json",
) -> None:
    """Configure structlog with JSON (production) or console (development) output.

    Args:
        log_level: Minimum log level. One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
        log_format: Output format.
            "json"    -- structured JSON lines, safe for log aggregators (default).
            "console" -- human-readable output for local development only.
                         Must NOT be set in deployed environments.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "console":
        # Use ANSI colours only when stdout is an interactive terminal to prevent
        # ANSI injection in CI log viewers, web-based log UIs, or piped output.
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=sys.stdout.isatty()
        )
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
