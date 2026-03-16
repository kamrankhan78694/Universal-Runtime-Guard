# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- `CONTRIBUTING.md` with development setup, coding standards, and PR process.
- `CHANGELOG.md` following Keep a Changelog format.
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
- GitHub Actions CI workflow for Python 3.8–3.12.
- Issue templates for bug reports and feature requests.
- Pull request template with checklist.
- Code coverage reporting via `pytest-cov`.
- Thread-safety stress tests for `api_guard.install()` / `uninstall()`.
- Asyncio edge-case tests (cancelled tasks, error propagation).
- Mermaid architecture diagrams in `ARCHITECTURE.md`.
- Badges in `README.md` (CI, Python versions, licence).
- `guard-core/` Rust workspace scaffold.

---

## [0.2.0] — 2025-06-15

### Added

- **File-based configuration** — `guard.toml` and `pyproject.toml [tool.guard]`
  section support via `guard/config.py`.
- **Type-aware API schema validation** — schemas like `{"id": int, "name": str}`
  now check types, not just key presence.
- **Nested schema validation** — `{"user": {"id": int}}` deep validation.
- **List schema validation** — `{"items": [{"id": int}]}` array validation.
- **Thread exception coverage** — `threading.excepthook` integration for
  catching exceptions in spawned threads.
- **Asyncio exception coverage** — custom asyncio loop exception handler.
- **CLI command** — `guard audit` with `--json` and `--broken` flags
  (`guard/__main__.py`).
- **Structured logging** — JSON-formatted log output via `guard/logging.py`.
- 40 new tests (total: 87, 100% pass rate).

---

## [0.1.0] — 2025-03-01

### Added

- **Dependency scanner** — static CVE database covering 11 packages with 20+
  CVE entries. Blocked-package detection for known-malicious packages.
  Optional broken-import scanning.
- **API Guard** — monkey-patches `requests.Session.send` to warn on bad status
  codes, validate JSON content types, detect key-level schema mismatches, and
  sanitise control characters from response bodies.
- **Error handler** — enriched `sys.excepthook` with branded error reports,
  per-type error counting, and optional auto-patch / crash suppression mode.
- **Fix advisor** — 30+ heuristic regex patterns matching exception messages to
  actionable fix suggestions.
- **Public API** — `guard.activate()` / `guard.deactivate()` entry points.
- **Modern packaging** — `pyproject.toml` with setuptools, pip-installable.
- 47 tests with 100% pass rate.
- `README.md` with quick-start guide and API reference.
- `ARCHITECTURE.md` describing the Rust-core, polyglot-wrapper target design.
- `DEVELOPMENT.md` with phase-by-phase roadmap.

---

[Unreleased]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/releases/tag/v0.1.0
