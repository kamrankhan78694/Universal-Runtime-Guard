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

Current phase
-------------
**Phase 1 — Single-process Python guard** (shipped).
All three layers operate within a single Python process.  Activation is
synchronous and takes < 1 ms.  The dependency scan runs at import time.

Next phases
-----------
**Phase 2 — Configuration file support** (planned).
Read ``guard.toml`` or a ``[tool.guard]`` section in ``pyproject.toml`` so
teams can version-control their guard settings without changing application
code.

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


def activate(
    *,
    check_dependencies: bool = True,
    check_broken: bool = False,
    guard_api: bool = True,
    expected_api_schema: Optional[dict] = None,
    guard_errors: bool = True,
    auto_patch: bool = False,
    verbose: bool = True,
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
        JSON API responses.  Mismatches trigger a schema-mismatch warning.
    guard_errors:
        Install an enriched ``sys.excepthook`` that prints rich error
        reports and suggests fixes.
    auto_patch:
        When ``True`` (and ``guard_errors`` is also ``True``), non-fatal
        unhandled exceptions are *suppressed* instead of crashing the
        process.  Only recommended for long-running services.
    verbose:
        Print a startup banner and a summary of activated layers.
    """
    activated: list[str] = []

    if check_dependencies:
        warnings = dependency.run_all_scans(check_broken=check_broken)
        for w in warnings:
            print(w, file=sys.stderr)
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
