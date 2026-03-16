"""
core.py — Main entry point for Universal Runtime Guard.

Overview
--------
This module exposes the two public top-level functions that callers interact
with most of the time:

* :func:`activate` — installs all protection layers in one shot.
* :func:`deactivate` — removes all guard hooks (useful in tests and REPL
  sessions).

Protection layers
~~~~~~~~~~~~~~~~~
+---------------------------+------------------------------------------+
| Layer                     | Controlled by                            |
+===========================+==========================================+
| Dependency scanner        | ``check_dependencies`` / ``check_broken``|
+---------------------------+------------------------------------------+
| API guard                 | ``guard_api`` / ``expected_api_schema``  |
+---------------------------+------------------------------------------+
| Error handler             | ``guard_errors`` / ``auto_patch``        |
+---------------------------+------------------------------------------+

Each layer can be independently disabled, e.g. when running inside a
testing framework that manages its own exception hooks.

Typical one-liner usage::

    import guard
    guard.activate()

Selective activation::

    import guard
    guard.activate(
        check_dependencies=True,
        guard_api=True,
        expected_api_schema={"id": int, "status": str},
        guard_errors=True,
        auto_patch=False,   # still exit on crash, but enrich the output
        verbose=True,
    )

Configuration file support::

    # Reads settings from guard.toml or pyproject.toml [tool.guard]
    guard.activate()

Current phase
-------------
**Phase 2 — Configuration, threading, async, and structured logging** (shipped).
All layers can be configured via ``guard.toml`` or ``pyproject.toml
[tool.guard]``.  Thread and asyncio exception coverage is active by default.
Structured JSON logging can be enabled with ``structured_logging=True``.

Next phases
-----------
**Phase 3 — Rust core & multi-language wrappers** (planned).
Port the core engine to a Rust crate (``guard-core``).  The Python package
becomes a thin PyO3 binding over the shared Rust library.  Node.js (napi-rs)
and Go (cgo) wrappers are published through their native package managers.
Each ecosystem gets a single ``activate()`` call.  See ``ARCHITECTURE.md``.

**Phase 4 — CI/CD integration** (planned).
A ``guard audit`` CLI command will scan a project's dependency tree and
return a non-zero exit code when vulnerabilities are found, enabling
gate-keeping in GitHub Actions / GitLab CI / Jenkins pipelines.

**Phase 5 — Dashboard, alerting & AI-workflow integration** (future).
An optional lightweight sidecar (``guard serve``) exposes a Prometheus
metrics endpoint and a web UI showing live error counts, suppressed crash
events, and dependency health.  Guard suggestions attach to the IDE
diagnostic channel so AI assistants (GitHub Copilot, Cursor) can auto-fix
flagged errors.
"""

from __future__ import annotations

import sys
from typing import Optional

from guard import api_guard, dependency, error_handler
from guard import logging as guard_logging
from guard.config import load_config


_UNSET = object()


def activate(
    *,
    check_dependencies: object = _UNSET,
    check_broken: object = _UNSET,
    guard_api: object = _UNSET,
    expected_api_schema: object = _UNSET,
    guard_errors: object = _UNSET,
    auto_patch: object = _UNSET,
    verbose: object = _UNSET,
    structured_logging: object = _UNSET,
    config_dir: Optional[str] = None,
) -> None:
    """
    Activate all Universal Runtime Guard protection layers.

    Parameters
    ----------
    check_dependencies:
        Scan installed packages for known vulnerabilities and blocked
        packages.  Warnings are printed to *stderr*.
    check_broken:
        Also scan for packages that are installed but fail to import.
        Disabled by default because iterating all packages has latency.
    guard_api:
        Monkey-patch ``requests`` so every HTTP response is validated and
        sanitised automatically.
    expected_api_schema:
        An optional ``dict`` whose keys define the fields you expect in
        JSON API responses.  Values can be ``None`` (presence-only), Python
        types (``int``, ``str``, …) for type checking, nested ``dict``
        schemas, or ``[{…}]`` for list-of-object schemas.
    guard_errors:
        Install an enriched ``sys.excepthook`` that prints rich error
        reports and suggests fixes.  Also installs ``threading.excepthook``
        and an asyncio exception handler.
    auto_patch:
        When ``True`` (and ``guard_errors`` is also ``True``), non-fatal
        unhandled exceptions are *suppressed* instead of crashing the
        process.  Only recommended for long-running services.
    verbose:
        Print a startup banner and a summary of activated layers.
    structured_logging:
        When ``True``, emit guard events as structured JSON log records
        to *stderr* via the standard :mod:`logging` module.
    config_dir:
        Directory to search for ``guard.toml`` or ``pyproject.toml``.
        Defaults to the current working directory.  Explicit keyword
        arguments always override file-based settings.
    """
    # --- Input validation (before any work) ----------------------------------
    if config_dir is not None and not isinstance(config_dir, str):
        raise TypeError(
            f"config_dir must be a str or None, got {type(config_dir).__name__}"
        )

    # Load config file defaults, then overlay explicit arguments.
    file_config = load_config(directory=config_dir)

    # Merge: explicit arguments take priority over file config, which takes
    # priority over built-in defaults.
    def _resolve(explicit: object, key: str, default: object) -> object:
        if explicit is not _UNSET:
            return explicit
        if key in file_config:
            return file_config[key]
        return default

    ck_dep = bool(_resolve(check_dependencies, "check_dependencies", True))
    ck_broken = bool(_resolve(check_broken, "check_broken", False))
    g_api = bool(_resolve(guard_api, "guard_api", True))
    schema = _resolve(expected_api_schema, "expected_api_schema", None)
    g_errors = bool(_resolve(guard_errors, "guard_errors", True))
    a_patch = bool(_resolve(auto_patch, "auto_patch", False))
    v = bool(_resolve(verbose, "verbose", True))
    s_logging = bool(_resolve(structured_logging, "structured_logging", False))

    if schema is not None and not isinstance(schema, dict):
        raise TypeError(
            f"expected_api_schema must be a dict or None, got {type(schema).__name__}"
        )

    activated: list[str] = []

    # Structured logging
    if s_logging:
        guard_logging.enable()

    if ck_dep:
        warnings = dependency.run_all_scans(check_broken=ck_broken)
        for w in warnings:
            print(w, file=sys.stderr)
            if guard_logging.is_enabled():
                guard_logging.log_event(
                    "dependency_warning", message=w,
                )
        activated.append("dependency scanner")

    if g_api:
        api_guard.install(expected_schema=schema if isinstance(schema, dict) else None)
        activated.append("API guard")

    if g_errors:
        error_handler.install(auto_patch=a_patch)
        activated.append("error handler")

    if v:
        layers = ", ".join(activated) if activated else "none"
        print(
            f"🛡️  Universal Runtime Guard activated — layers: {layers}",
            file=sys.stderr,
        )


def deactivate() -> None:
    """Remove all guard hooks (useful in tests or REPL sessions)."""
    api_guard.uninstall()
    error_handler.uninstall()
    guard_logging.disable()
