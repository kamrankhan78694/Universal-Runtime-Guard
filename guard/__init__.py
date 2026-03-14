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
  suggestions alongside every unhandled exception traceback.

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

   Current release version string (e.g. ``"0.1.0"``).

Development phases
------------------
**Phase 1 (current)** — Core Python package with static vulnerability DB,
requests monkey-patch, and heuristic error advisor.

**Phase 2 (planned)** — Configuration file support, type-aware API schema
validation, and thread/async exception coverage.

**Phase 3 (planned)** — Node.js / Go / Rust language ports via shared Rust
core; CI/CD ``guard audit`` CLI command.

**Phase 4 (planned)** — Live OSV advisory DB integration; SBOM export.

**Phase 5 (future)** — Optional dashboard sidecar, remote error reporting,
and LLM-powered fix suggestions.

See ``DEVELOPMENT.md`` for the full roadmap.
"""

from guard.core import activate, deactivate
from guard.error_handler import error_counts, reset_counts

__all__ = [
    "activate",
    "deactivate",
    "error_counts",
    "reset_counts",
]

__version__ = "0.1.0"
