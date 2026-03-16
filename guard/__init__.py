"""
Universal Runtime Guard
=======================

A single dependency that automatically prevents crashes, security exploits,
and bad API responses in production.

Quick start::

    import guard
    guard.activate()

After calling ``activate()`` the guard:

* scans installed packages for known CVEs and blocked packages (stderr);
* patches ``requests`` so every HTTP response is validated and sanitised;
* installs an enriched ``sys.excepthook`` that prints actionable fix
  suggestions alongside every unhandled exception traceback;
* installs ``threading.excepthook`` for worker-thread coverage;
* optionally emits structured JSON log records for log aggregators.

Settings can be loaded from ``guard.toml`` or ``pyproject.toml [tool.guard]``
so teams can version-control their configuration without changing code.

Public API
----------
.. autofunction:: activate
.. autofunction:: deactivate
.. autofunction:: error_counts
.. autofunction:: reset_counts

Package version
---------------
.. data:: __version__
   :type: str

   Current release version string (e.g. ``"0.3.0"``).

Development phases
------------------
**Phase 1 (shipped)** — Core Python package with static vulnerability DB,
requests monkey-patch, and heuristic error advisor.

**Phase 2 (shipped)** — Configuration file support, type-aware API schema
validation, thread/async exception coverage, ``guard audit`` CLI command,
and structured logging output.

**Phase 3 (current)** — Thread-safe error counting and API guard locking,
asyncio handler auto-installation, structured logging integration in error
and API layers, Rust core scaffold, CI/CD, contributor infrastructure.

**Phase 4 (planned)** — Live OSV advisory DB integration; SBOM export.

**Phase 5 (future)** — Optional dashboard sidecar, remote error reporting,
LLM-powered fix suggestions, and AI-workflow integration.

See ``ARCHITECTURE.md`` for the Rust-core design and ``DEVELOPMENT.md`` for
the full roadmap.
"""

from guard.core import activate, deactivate
from guard.error_handler import error_counts, reset_counts

__all__ = [
    "activate",
    "deactivate",
    "error_counts",
    "reset_counts",
]

__version__ = "0.3.0"
