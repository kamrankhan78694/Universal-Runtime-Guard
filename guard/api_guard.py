"""
api_guard.py — API response sanitisation via a requests monkey-patch.

Overview
--------
This module wraps ``requests.Session.send`` so that every HTTP response the
application receives is automatically validated and sanitised *before* it
reaches application code.  The wrapping is transparent: the returned object
behaves like a normal :class:`requests.Response` (all attributes are
forwarded) but adds:

* **Status-code warnings** — prints a ``⚠️`` to *stderr* for 3xx, 4xx and
  5xx responses so they are never silently swallowed.
* **Content-Type / JSON validation** — checks that a response claiming to
  be JSON actually contains valid JSON, and optionally verifies that the
  top-level keys match an *expected_schema* supplied at install time.
* **String sanitisation** — :meth:`_GuardedResponse.json` and
  :meth:`_GuardedResponse.sanitized_text` strip ASCII control characters
  (0x00–0x08, 0x0B, 0x0C, 0x0E–0x1F, 0x7F) that could indicate injection
  payloads.

Usage
~~~~~
:func:`install` is called automatically by :func:`guard.core.activate`.
It can also be called directly::

    from guard.api_guard import install
    install(expected_schema={"id": None, "name": None})

Call :func:`uninstall` to restore the original ``requests.Session.send``
(useful in tests or interactive sessions).

Thread safety
~~~~~~~~~~~~~
:func:`install` and :func:`uninstall` are not thread-safe.  Call them
once at application start-up before spawning threads.

Current phase
-------------
**Phase 1 — Synchronous requests patching** (shipped).
Only the ``requests`` library is patched.  Schema validation is key-based
(presence/absence only, not type-checked).

Next phases
-----------
**Phase 2 — Type-aware schema validation** (planned).
Extend schema checking to validate value types (``{"id": int, "name": str}``)
and nested structures so mismatches are caught at the field level.  In
Phase 1 schema values are ignored — only key presence/absence is checked.

**Phase 3 — httpx / aiohttp support** (planned).
Provide equivalent async-compatible wrappers for ``httpx.AsyncClient`` and
``aiohttp.ClientSession`` so async-first applications get the same
protection with no extra configuration.

**Phase 4 — OpenAPI / JSON-Schema integration** (future).
Accept a full OpenAPI 3.x spec or JSON Schema document as the
``expected_schema`` and validate responses against it automatically.

**Phase 5 — Rate-limit and latency alerting** (future).
Track response times per host and warn when p99 latency exceeds a
configurable threshold, or when the ``Retry-After`` / ``X-RateLimit-*``
headers indicate throttling.
"""

from __future__ import annotations

import re
import sys
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_value(value: Any) -> Any:
    """Recursively strip dangerous control characters from string values."""
    if isinstance(value, str):
        return _CONTROL_CHAR_RE.sub("", value)
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------

class _GuardedResponse:
    """
    A thin proxy around a :class:`requests.Response` that adds validation
    helpers.  It forwards all attribute access to the real response object so
    callers do not need to change their code.
    """

    def __init__(self, response: Any, expected_schema: Optional[dict] = None) -> None:
        self._response = response
        self._expected_schema = expected_schema
        self._validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        self._check_status()
        self._check_content_type()

    def _check_status(self) -> None:
        status = self._response.status_code
        if status >= 500:
            _warn(
                f"⚠️  API response: server error {status} from "
                f"{self._response.url}"
            )
        elif status >= 400:
            _warn(
                f"⚠️  API response: client error {status} from "
                f"{self._response.url}"
            )
        elif status >= 300:
            _warn(
                f"⚠️  API response: unexpected redirect {status} from "
                f"{self._response.url}"
            )

    def _check_content_type(self) -> None:
        content_type = self._response.headers.get("Content-Type", "")
        if "json" in content_type:
            self._validate_json()

    def _validate_json(self) -> None:
        try:
            data = self._response.json()
        except Exception:
            _warn(
                f"⚠️  Detected API schema mismatch: response from "
                f"{self._response.url} claims JSON content-type but "
                f"body is not valid JSON."
            )
            return

        if self._expected_schema is not None:
            missing = set(self._expected_schema) - set(data if isinstance(data, dict) else {})
            extra = set(data if isinstance(data, dict) else {}) - set(self._expected_schema)
            if missing:
                _warn(
                    f"⚠️  Detected API schema mismatch: response from "
                    f"{self._response.url} is missing expected keys: "
                    f"{sorted(missing)}"
                )
            if extra:
                _warn(
                    f"⚠️  Detected API schema mismatch: response from "
                    f"{self._response.url} contains unexpected keys: "
                    f"{sorted(extra)}"
                )

    # ------------------------------------------------------------------
    # Sanitised json() shortcut
    # ------------------------------------------------------------------

    def json(self, **kwargs: Any) -> Any:
        """Return parsed JSON with control characters stripped from strings."""
        raw = self._response.json(**kwargs)
        return _sanitize_value(raw)

    def sanitized_text(self) -> str:
        """Return the response body text with control characters stripped."""
        return _sanitize_value(self._response.text)

    # ------------------------------------------------------------------
    # Transparent proxy
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    def __repr__(self) -> str:
        return f"<GuardedResponse [{self._response.status_code}]>"


# ---------------------------------------------------------------------------
# Monkey-patch
# ---------------------------------------------------------------------------

_original_send: Any = None
_installed = False


def install(expected_schema: Optional[dict] = None) -> None:
    """
    Monkey-patch ``requests.Session.send`` so every response is wrapped in a
    :class:`_GuardedResponse`.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _original_send, _installed
    if _installed:
        return

    try:
        import requests  # noqa: PLC0415

        _original_send = requests.Session.send

        def _guarded_send(session_self: Any, *args: Any, **kwargs: Any) -> Any:
            response = _original_send(session_self, *args, **kwargs)
            return _GuardedResponse(response, expected_schema=expected_schema)

        requests.Session.send = _guarded_send  # type: ignore[method-assign]
        _installed = True
    except ImportError:
        # requests is not installed — nothing to patch.
        pass


def uninstall() -> None:
    """Restore the original ``requests.Session.send``."""
    global _original_send, _installed
    if not _installed or _original_send is None:
        return
    try:
        import requests  # noqa: PLC0415

        requests.Session.send = _original_send  # type: ignore[method-assign]
    except ImportError:
        pass
    _original_send = None
    _installed = False
