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


def activate(
    *,
    check_dependencies: bool = True,
    check_broken: bool = False,
    guard_api: bool = True,
    expected_api_schema: Optional[dict] = None,
    guard_errors: bool = True,
    auto_patch: bool = False,
    verbose: bool = True,
    structured_logging: bool = False,
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
    # Load config file defaults, then overlay explicit arguments.
    file_config = load_config(directory=config_dir)

    # Apply file config as defaults — explicit arguments take priority.
    # We detect "not explicitly passed" by inspecting the call vs defaults.
    # Since all params have defaults, we use file_config only when present.
    if "check_dependencies" in file_config and check_dependencies is True:
        check_dependencies = file_config["check_dependencies"]
    if "check_broken" in file_config and check_broken is False:
        check_broken = file_config["check_broken"]
    if "guard_api" in file_config and guard_api is True:
        guard_api = file_config["guard_api"]
    if "guard_errors" in file_config and guard_errors is True:
        guard_errors = file_config["guard_errors"]
    if "auto_patch" in file_config and auto_patch is False:
        auto_patch = file_config["auto_patch"]
    if "verbose" in file_config and verbose is True:
        verbose = file_config["verbose"]
    if "expected_api_schema" in file_config and expected_api_schema is None:
        expected_api_schema = file_config["expected_api_schema"]

    activated: list[str] = []

    # Structured logging
    if structured_logging:
        guard_logging.enable()

    if check_dependencies:
        warnings = dependency.run_all_scans(check_broken=check_broken)
        for w in warnings:
            print(w, file=sys.stderr)
            if guard_logging.is_enabled():
                guard_logging.log_event(
                    "dependency_warning", message=w,
                )
        activated.append("dependency scanner")

    if guard_api:
        api_guard.install(expected_schema=expected_api_schema)
        activated.append("API guard")

    if guard_errors:
        error_handler.install(auto_patch=auto_patch)
        activated.append("error handler")

    if verbose:
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
