# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] — 2026-03-16

### Added

- **Structured logging in error handler** — error hooks now emit JSON log
  events (`unhandled_exception`) when structured logging is enabled, so error
  events flow to log aggregators alongside human-readable output.
- **Structured logging in API guard** — API warnings now emit JSON log events
  (`api_warning`) when structured logging is enabled.
- **Input validation** — `activate()` raises `TypeError` for invalid
  `expected_api_schema` (must be `dict` or `None`) and `config_dir`
  (must be `str` or `None`).
- **Defensive error handling** — error hooks wrap `advisor.suggest()` calls
  in try/except so a broken advisor never crashes the host application.
- **SECURITY.md** — security policy with vulnerability reporting guidelines.
- **`.pre-commit-config.yaml`** — pre-commit hooks for trailing whitespace,
  YAML/TOML validation, import sorting, `guard audit`, and pre-push pytest.
- `CONTRIBUTING.md` with development setup, coding standards, and PR process.
- `CHANGELOG.md` following Keep a Changelog format.
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
- GitHub Actions CI workflow for Python 3.8–3.12 on Linux, macOS, Windows.
- Issue templates for bug reports and feature requests.
- Pull request template with checklist.
- Code coverage reporting via `pytest-cov` (88% coverage).
- Thread-safety stress tests for `api_guard.install()` / `uninstall()`.
- Asyncio edge-case tests (cancelled tasks, concurrent failures, no traceback).
- Production hardening tests (thread-safe counts, input validation, structured
  logging, defensive hooks).
- Mermaid architecture diagrams in `ARCHITECTURE.md`.
- Badges in `README.md` (CI, Python versions, licence).
- `guard-core/` Rust workspace scaffold with scanner, sanitiser, and advisor.

### Fixed

- **Thread-safe error counting** — `_error_counts` is now protected by
  `threading.Lock`, preventing data races when exceptions occur in multiple
  threads simultaneously.
- **Thread-safe API guard install/uninstall** — `install()` and `uninstall()`
  are now protected by an internal lock, preventing races during concurrent
  calls.
- **Asyncio handler auto-installation** — `error_handler.install()` now
  attempts to install the asyncio exception handler on the running event loop
  (if one exists), so async applications get coverage without manual setup.
- **DeprecationWarning** — replaced `asyncio.get_event_loop()` with
  `asyncio.get_running_loop()` to avoid warnings on Python 3.12+.

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

[Unreleased]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kamrankhan78694/Universal-Runtime-Guard/releases/tag/v0.1.0
