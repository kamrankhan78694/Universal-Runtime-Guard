"""
advisor.py — Heuristic fix suggestions for common runtime errors.

Overview
--------
This module provides a single public function, :func:`suggest`, which accepts
an exception type and value and returns a human-readable, actionable
suggestion string (or ``None`` when no pattern matches).

How it works
~~~~~~~~~~~~
A static list of ``(regex_pattern, suggestion_template)`` pairs is matched
against both the raw exception message and the ``"TypeName: message"``
composite form.  The composite form handles exception types such as
:class:`KeyError` whose ``__str__`` omits the class name.

Captured regex groups are interpolated into the template via
:meth:`str.format` so that, for example, the missing module name from a
:class:`ModuleNotFoundError` is surfaced directly in the suggestion.

Extending the rule set
~~~~~~~~~~~~~~~~~~~~~~
Add a tuple to :data:`_SUGGESTIONS`::

    (r"<regex>", "Human-readable suggestion. Use {0}, {1} … for capture groups."),

The list is evaluated in order; the *first* match wins.

Current phase
-------------
**Phase 1 — Static heuristics** (shipped).
Rules are hard-coded regular-expression patterns.  No external calls are
made, keeping the module dependency-free and instantaneous.

Next phases
-----------
**Phase 2 — Dynamic context enrichment** (planned).
Attach local variable values and the last few log lines to the suggestion
so the developer sees *why* the value was wrong, not just *that* it was.

**Phase 3 — LLM-powered suggestions** (future).
For errors that match no static pattern, optionally call a locally-running
or remote LLM (opt-in, never on by default) to generate a free-form
suggestion.  The interface will remain identical — callers always get a
plain string or ``None``.
"""

from __future__ import annotations

import re
from typing import Optional

# Mapping of error patterns to human-readable suggestions.
_SUGGESTIONS: list[tuple[str, str]] = [
    # Import errors
    (r"No module named '(.+)'",
     "Run `pip install {0}` to install the missing package."),
    (r"cannot import name '(.+)' from '(.+)'",
     "'{0}' may have been removed or renamed in '{1}'. Check the changelog and update your import."),
    # Attribute errors
    (r"'(.+)' object has no attribute '(.+)'",
     "Check the API of '{0}': attribute '{1}' may have been renamed or removed in a newer version."),
    # Type errors
    (r"unsupported operand type\(s\) for (.+): '(.+)' and '(.+)'",
     "You are mixing types '{1}' and '{2}'. Consider explicit type conversion before the operation."),
    (r"'(.+)' object is not (callable|iterable|subscriptable)",
     "'{0}' is not {1}. Verify you are using the correct variable or function."),
    # Key / Index errors
    (r"KeyError: (.+)",
     "Key {0} was not found. Use `.get()` with a default value or check membership with `in`."),
    (r"list index out of range",
     "You are accessing a list index that does not exist. Check the list length before indexing."),
    # Value errors
    (r"invalid literal for int\(\) with base \d+: '(.+)'",
     "'{0}' cannot be converted to an integer. Validate or sanitize the input first."),
    # File errors
    (r"No such file or directory: '(.+)'",
     "The file or directory '{0}' does not exist. Check the path and ensure the file is present."),
    (r"Permission denied: '(.+)'",
     "Insufficient permissions to access '{0}'. Check file permissions or run with elevated privileges."),
    # Connection errors
    (r"Connection refused",
     "The remote server refused the connection. Verify the host, port, and that the service is running."),
    (r"getaddrinfo failed",
     "DNS resolution failed. Check the hostname and your network connection."),
    # Timeout
    (r"timed out",
     "The operation timed out. Consider increasing the timeout or checking the remote service health."),
    # Recursion
    (r"maximum recursion depth exceeded",
     "Infinite or very deep recursion detected. Add a base case or increase `sys.setrecursionlimit()` carefully."),
    # Memory
    (r"(MemoryError|Cannot allocate memory)",
     "The process ran out of memory. Reduce data size, stream data incrementally, or add more RAM."),
    # ZeroDivision
    (r"division by zero",
     "You are dividing by zero. Guard the divisor with an `if divisor != 0` check."),
    # SSL
    (r"SSL(Error|CertVerificationError|Certificate)",
     "SSL verification failed. Ensure certificates are up to date and avoid disabling SSL verification in production."),
    # JSON
    (r"Expecting value: line \d+ column \d+",
     "The response is not valid JSON. Check that the server is returning JSON and the Content-Type header is correct."),
]


def suggest(exc_type: type, exc_value: BaseException) -> Optional[str]:
    """Return a human-readable fix suggestion for *exc_value*, or ``None``."""
    message = str(exc_value)
    type_name = exc_type.__name__
    # Some exceptions (e.g. KeyError) omit the class name from str(exc),
    # so we also match against the "TypeName: message" composite form.
    full_message = f"{type_name}: {message}"

    for pattern, template in _SUGGESTIONS:
        match = re.search(pattern, message, re.IGNORECASE) or re.search(
            pattern, full_message, re.IGNORECASE
        )
        if match:
            try:
                suggestion = template.format(*match.groups())
            except IndexError:
                suggestion = template
            return f"💡 Suggestion [{type_name}]: {suggestion}"

    return None
