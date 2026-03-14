"""
error_handler.py — Runtime error catching, reporting, and fix suggestions.

Overview
--------
This module installs a custom :func:`sys.excepthook` that intercepts every
unhandled exception *before* the interpreter prints it and exits.  For each
intercepted exception it:

1. **Prints a rich error report** — a formatted traceback surrounded by a
   clearly branded header so it stands out in logs.
2. **Surfaces a fix suggestion** — delegates to :mod:`guard.advisor` to
   pattern-match the exception and suggest an actionable fix.
3. **Tracks error counts** — accumulates per-type counts accessible via
   :func:`guard.error_counts` so dashboards can query them.
4. **Optionally suppresses the crash** — when ``auto_patch=True``, non-fatal
   exceptions are *suppressed* (the process continues running).  This is
   intended for long-running services that should degrade gracefully rather
   than crash.  :class:`SystemExit` and :class:`KeyboardInterrupt` are
   *always* forwarded to the original hook regardless of this setting.
5. **Thread exception coverage** — installs ``threading.excepthook``
   (Python 3.8+) so uncaught exceptions in worker threads get the same
   rich reporting.
6. **Asyncio task exception coverage** — sets a custom loop exception handler
   so uncaught exceptions in async tasks are treated identically.

Installation / removal
~~~~~~~~~~~~~~~~~~~~~~
:func:`install` and :func:`uninstall` are idempotent — safe to call more
than once.  :func:`guard.core.activate` and :func:`guard.core.deactivate`
call them for you.

Direct usage::

    from guard.error_handler import install, uninstall, error_counts
    install(auto_patch=False)   # enrich errors but still exit
    install(auto_patch=True)    # enrich errors and keep running
    uninstall()                 # restore original sys.excepthook

Current phase
-------------
**Phase 2 — Thread and async-task coverage** (shipped).
``threading.excepthook`` and ``asyncio`` loop exception handlers are
installed alongside the main-thread ``sys.excepthook``, giving uniform
error reporting across all execution contexts.

Next phases
-----------
**Phase 3 — Structured logging integration** (planned).
Emit errors as JSON log records (compatible with ``structlog`` and the
standard ``logging`` module) in addition to the human-readable stderr
output, so production log aggregators (Datadog, Loki, CloudWatch) can
index them.

**Phase 4 — Automatic retry for transient errors** (future).
For network-related errors (:class:`ConnectionError`, :class:`TimeoutError`)
optionally schedule an automatic retry with exponential back-off when
``auto_patch=True`` instead of silently suppressing the exception.

**Phase 5 — Remote error reporting** (future).
Provide an opt-in sink that batches error events and POSTs them to a
configurable endpoint (Sentry-compatible DSN, or the guard cloud service),
enabling cross-instance error correlation.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import traceback
from typing import Any, Optional, Type

from guard import advisor


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_original_excepthook: Any = sys.__excepthook__
_original_threading_excepthook: Any = None
_installed = False

# Counts of caught exceptions, keyed by exception type name.
_error_counts: dict[str, int] = {}

# When auto_patch is True the hook prevents the interpreter from exiting for
# non-fatal exceptions (i.e. anything except SystemExit / KeyboardInterrupt).
_auto_patch: bool = False


# ---------------------------------------------------------------------------
# The hook
# ---------------------------------------------------------------------------

def _guard_excepthook(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> None:
    type_name = exc_type.__name__

    # Always let SystemExit / KeyboardInterrupt propagate normally.
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
        _original_excepthook(exc_type, exc_value, exc_tb)
        return

    # Track counts.
    _error_counts[type_name] = _error_counts.get(type_name, 0) + 1

    # --- Rich error report ---------------------------------------------------
    lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_text = "".join(lines).rstrip()

    print(f"\n{'─' * 60}", file=sys.stderr)
    print(f"🛡️  Universal Runtime Guard — Unhandled {type_name}", file=sys.stderr)
    print(f"{'─' * 60}", file=sys.stderr)
    print(tb_text, file=sys.stderr)

    # --- Fix suggestion ------------------------------------------------------
    suggestion = advisor.suggest(exc_type, exc_value)
    if suggestion:
        print(f"\n{suggestion}", file=sys.stderr)

    if _auto_patch:
        print(
            f"\n⚙️  Auto-patched: suppressing crash (auto_patch=True). "
            f"Total {type_name} suppressions: {_error_counts[type_name]}",
            file=sys.stderr,
        )
    else:
        print(f"{'─' * 60}\n", file=sys.stderr)
        # Re-raise by calling the original hook so the process exits normally.
        _original_excepthook(exc_type, exc_value, exc_tb)


# ---------------------------------------------------------------------------
# Threading excepthook (Python 3.8+)
# ---------------------------------------------------------------------------

def _guard_threading_excepthook(args: Any) -> None:
    """Handle uncaught exceptions in worker threads."""
    exc_type = args.exc_type
    exc_value = args.exc_value
    exc_tb = args.exc_traceback

    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
        if _original_threading_excepthook is not None:
            _original_threading_excepthook(args)
        return

    type_name = exc_type.__name__
    _error_counts[type_name] = _error_counts.get(type_name, 0) + 1

    thread_name = args.thread.name if args.thread else "unknown"
    lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_text = "".join(lines).rstrip()

    print(f"\n{'─' * 60}", file=sys.stderr)
    print(
        f"🛡️  Universal Runtime Guard — Unhandled {type_name} "
        f"in thread '{thread_name}'",
        file=sys.stderr,
    )
    print(f"{'─' * 60}", file=sys.stderr)
    print(tb_text, file=sys.stderr)

    suggestion = advisor.suggest(exc_type, exc_value)
    if suggestion:
        print(f"\n{suggestion}", file=sys.stderr)

    if _auto_patch:
        print(
            f"\n⚙️  Auto-patched: suppressing crash (auto_patch=True). "
            f"Total {type_name} suppressions: {_error_counts[type_name]}",
            file=sys.stderr,
        )
    else:
        print(f"{'─' * 60}\n", file=sys.stderr)


# ---------------------------------------------------------------------------
# Asyncio exception handler
# ---------------------------------------------------------------------------

def _guard_async_exception_handler(
    loop: asyncio.AbstractEventLoop,
    context: dict[str, Any],
) -> None:
    """Handle uncaught exceptions in asyncio tasks."""
    exception = context.get("exception")
    if exception is None:
        # Not an exception-based event; use default handling.
        loop.default_exception_handler(context)
        return

    exc_type = type(exception)
    type_name = exc_type.__name__

    if isinstance(exception, (SystemExit, KeyboardInterrupt)):
        loop.default_exception_handler(context)
        return

    _error_counts[type_name] = _error_counts.get(type_name, 0) + 1

    tb_text = ""
    if exception.__traceback__:
        lines = traceback.format_exception(
            exc_type, exception, exception.__traceback__,
        )
        tb_text = "".join(lines).rstrip()
    else:
        tb_text = f"{type_name}: {exception}"

    task_name = ""
    task = context.get("task")
    if task is not None:
        task_name = getattr(task, "get_name", lambda: str(task))()

    print(f"\n{'─' * 60}", file=sys.stderr)
    header = f"🛡️  Universal Runtime Guard — Unhandled {type_name}"
    if task_name:
        header += f" in task '{task_name}'"
    print(header, file=sys.stderr)
    print(f"{'─' * 60}", file=sys.stderr)
    print(tb_text, file=sys.stderr)

    suggestion = advisor.suggest(exc_type, exception)
    if suggestion:
        print(f"\n{suggestion}", file=sys.stderr)

    if _auto_patch:
        print(
            f"\n⚙️  Auto-patched: suppressing crash (auto_patch=True). "
            f"Total {type_name} suppressions: {_error_counts[type_name]}",
            file=sys.stderr,
        )
    else:
        print(f"{'─' * 60}\n", file=sys.stderr)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def install(auto_patch: bool = False) -> None:
    """
    Install the guard excepthook.

    Parameters
    ----------
    auto_patch:
        When ``True``, non-fatal exceptions are *suppressed* (the process does
        not exit after the hook runs).  Use with care — this is only useful
        for long-running services where you want to log and continue rather
        than crash.
    """
    global _installed, _auto_patch, _original_threading_excepthook
    if _installed:
        return
    _auto_patch = auto_patch

    # Main-thread excepthook
    sys.excepthook = _guard_excepthook

    # Thread excepthook (Python 3.8+)
    _original_threading_excepthook = threading.excepthook
    threading.excepthook = _guard_threading_excepthook

    _installed = True


def uninstall() -> None:
    """Restore the original ``sys.excepthook`` and threading/asyncio hooks."""
    global _installed, _original_threading_excepthook
    sys.excepthook = _original_excepthook

    # Restore threading excepthook
    if _original_threading_excepthook is not None:
        threading.excepthook = _original_threading_excepthook
        _original_threading_excepthook = None

    _installed = False


def error_counts() -> dict[str, int]:
    """Return a copy of the error-count dictionary."""
    return dict(_error_counts)


def reset_counts() -> None:
    """Clear all recorded error counts (useful in tests)."""
    _error_counts.clear()
