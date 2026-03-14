"""
logging.py — Structured JSON logging for Universal Runtime Guard.

Overview
--------
This module provides structured JSON logging output so guard events can be
indexed by log aggregators (Datadog, Loki, CloudWatch, etc.).

When enabled, every guard event (dependency warnings, API schema mismatches,
error handler reports) is *also* emitted as a JSON log record via the
standard :mod:`logging` module.

Usage
~~~~~
:func:`enable` creates a ``guard`` logger that writes JSON records to
*stderr*.  It is called automatically by :func:`guard.core.activate` when
``structured_logging=True``.

Direct usage::

    from guard.logging import enable, disable, log_event
    enable()
    log_event("dependency_warning", message="pyyaml==5.1.0 is vulnerable")
    disable()

Current phase
-------------
**Phase 2 — Structured logging output** (shipped).
JSON log records are emitted alongside human-readable output.

Next phases
-----------
**Phase 3 — structlog integration** (planned).
Optional deep integration with the ``structlog`` library for projects that
already use it.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Optional


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach extra fields set via log_event().
        if hasattr(record, "guard_event"):
            log_entry["event"] = record.guard_event
        if hasattr(record, "guard_data"):
            log_entry["data"] = record.guard_data
        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_logger: Optional[logging.Logger] = None
_handler: Optional[logging.Handler] = None
_enabled = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enable(level: int = logging.WARNING) -> logging.Logger:
    """
    Enable structured JSON logging for guard events.

    Returns the configured :class:`logging.Logger` instance.
    """
    global _logger, _handler, _enabled
    if _enabled and _logger is not None:
        return _logger

    _logger = logging.getLogger("guard")
    _logger.setLevel(level)

    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(_JsonFormatter())
    _logger.addHandler(_handler)

    _enabled = True
    return _logger


def disable() -> None:
    """Disable structured logging and remove the handler."""
    global _logger, _handler, _enabled
    if _logger is not None and _handler is not None:
        _logger.removeHandler(_handler)
    _handler = None
    _enabled = False


def is_enabled() -> bool:
    """Return whether structured logging is currently active."""
    return _enabled


def log_event(
    event: str,
    *,
    level: int = logging.WARNING,
    message: str = "",
    **data: Any,
) -> None:
    """
    Log a structured guard event.

    Parameters
    ----------
    event:
        Event type (e.g., ``"dependency_warning"``, ``"schema_mismatch"``,
        ``"unhandled_exception"``).
    level:
        Logging level.
    message:
        Human-readable message.
    **data:
        Additional key-value pairs included in the JSON record.
    """
    if not _enabled or _logger is None:
        return

    extra: dict[str, Any] = {"guard_event": event}
    if data:
        extra["guard_data"] = data
    _logger.log(level, message, extra=extra)
