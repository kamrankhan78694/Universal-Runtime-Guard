# Universal Runtime Guard — Development Roadmap

This document tracks the **current development phase** and every planned
future phase for the project.  It is updated as features ship or priorities
change.

> **Architecture:** This project follows a **Rust-core, polyglot-wrapper**
> pattern — a single Rust engine with thin, idiomatic wrappers for Python,
> Node.js, Go, and more.  Python is the "front door" for early adoption;
> Rust is the "engine room" for performance and cross-platform reach.
> See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design document.

---

## Legend

| Symbol | Meaning                    |
|--------|----------------------------|
| ✅     | Shipped in current release |
| 🔄     | In progress                |
| 📋     | Planned (next milestone)   |
| 🔭     | Future (backlog)           |

---

## Phase 1 — Core Python Package ✅

**Goal:** Deliver a working, installable Python package that can be activated
with a single `guard.activate()` call.

### Shipped features

| Feature | Module | Status |
|---------|--------|--------|
| Static vulnerability database (CVE-based) | `guard/dependency.py` | ✅ |
| Blocked-package detection | `guard/dependency.py` | ✅ |
| Broken-package scan (opt-in) | `guard/dependency.py` | ✅ |
| `requests` response monkey-patch | `guard/api_guard.py` | ✅ |
| Status-code warnings (3xx / 4xx / 5xx) | `guard/api_guard.py` | ✅ |
| JSON Content-Type validation | `guard/api_guard.py` | ✅ |
| Key-level API schema mismatch detection | `guard/api_guard.py` | ✅ |
| Control-character sanitisation of response bodies | `guard/api_guard.py` | ✅ |
| Enriched `sys.excepthook` | `guard/error_handler.py` | ✅ |
| Per-type error counting | `guard/error_handler.py` | ✅ |
| Auto-patch / crash suppression mode | `guard/error_handler.py` | ✅ |
| Heuristic fix suggestions (30+ patterns) | `guard/advisor.py` | ✅ |
| `guard.activate()` / `guard.deactivate()` public API | `guard/core.py` | ✅ |
| `pyproject.toml` packaging | `pyproject.toml` | ✅ |
| 47-test pytest suite (100 % pass) | `tests/` | ✅ |
| Full module docstrings with phase docs | all modules | ✅ |
| README quick-start + API reference | `README.md` | ✅ |
| Development roadmap | `DEVELOPMENT.md` | ✅ |

---

## Phase 2 — Configuration & Deeper Coverage ✅ (current)

**Goal:** Let teams configure guard via a file, extend API validation to
types, and cover async / threaded code paths.

### Shipped features

| Feature | Module | Status |
|---------|--------|--------|
| `guard.toml` / `pyproject.toml [tool.guard]` support | `guard/config.py` | ✅ |
| Type-aware API schema validation | `guard/api_guard.py` | ✅ |
| Nested / list schema validation | `guard/api_guard.py` | ✅ |
| Thread exception coverage (`threading.excepthook`) | `guard/error_handler.py` | ✅ |
| Asyncio task exception coverage | `guard/error_handler.py` | ✅ |
| `guard audit` CLI command | `guard/__main__.py` | ✅ |
| Structured logging output (JSON) | `guard/logging.py` | ✅ |
| 85-test pytest suite (100 % pass) | `tests/` | ✅ |

---

## Phase 3 — Rust Core & Multi-Language Wrappers 📋

**Goal:** Port the core engine to Rust and ship native wrappers for Node.js
and Go.  Python becomes a thin PyO3 binding over the shared Rust crate.
Each ecosystem gets a single `activate()` call published via its native
package manager.

> This follows the **Rust-core, polyglot-wrapper** architecture described in
> [`ARCHITECTURE.md`](ARCHITECTURE.md).  The Python Phase 1 implementation
> serves as the prototype and specification; every test becomes a contract
> that the Rust core must satisfy.

### Planned items

- [ ] **`guard-core` Rust crate**
  Implement the vulnerability scanner, API sanitiser, error advisor, and
  embedded advisory database in Rust.  Compile to a native shared library
  (`.so` / `.dylib` / `.dll`), a WASM module, and a standalone CLI binary.

- [ ] **Python PyO3 binding**
  Replace the pure-Python internals with calls to the compiled `guard-core`
  library via PyO3.  The public Python API (`guard.activate()`) stays
  identical — existing users see no change.

- [ ] **Node.js wrapper** (`npm install universal-runtime-guard`)
  A thin JS shim (via napi-rs) that hooks `process.on('uncaughtException')`
  and patches `node-fetch` / `axios`.

- [ ] **Go module**
  A `guard.Activate()` call that wraps `net/http.DefaultClient` and
  intercepts `panic` via `recover()`.

- [ ] **GitHub Actions workflow** (`.github/workflows/guard-audit.yml`)
  A reusable workflow that runs `guard audit` as a PR check.

- [ ] **Pre-commit hook**
  A `pre-commit` config entry that runs `guard audit` before every commit.

---

## Phase 4 — Live Advisory DB & Supply-Chain Tooling 🔭

**Goal:** Keep the vulnerability database current without requiring a package
upgrade, and support supply-chain compliance workflows.

### Planned items

- [ ] **Live OSV / PyPA Advisory DB integration**
  Optional `live=True` flag on `run_all_scans()` that fetches advisories
  from `https://osv.dev/query` and merges them with the built-in DB.
  Falls back to built-in DB when offline.

- [ ] **Advisory database caching**
  Cache live-fetched advisories to `~/.cache/guard/advisories.json` with a
  configurable TTL so repeated scans don't incur network overhead.

- [ ] **CycloneDX / SPDX SBOM export**
  `guard sbom --format cyclonedx > sbom.json` generates a Software Bill of
  Materials from the current environment, suitable for submission to
  customers or regulators.

- [ ] **Dependency graph conflict detection**
  Use `pip`'s resolver internals to surface version-conflict trees, not
  just individual package advisories.

- [ ] **Licence compliance scanning**
  Warn when installed packages use licences incompatible with a configurable
  allow-list (e.g., GPL in a proprietary project).

---

## Phase 5 — Dashboard, Alerting & LLM Suggestions 🔭

**Goal:** Provide operational visibility and leverage LLMs for richer
fix suggestions.

### Planned items

- [ ] **`guard serve` dashboard sidecar**
  A lightweight HTTP server (`uvicorn`) that exposes:
  - A Prometheus `/metrics` endpoint with error counts and dependency health.
  - A web UI (`/ui`) showing live events, suppressed crashes, and
    vulnerability alerts — zero changes to application code required.

- [ ] **Alert webhooks**
  Configurable webhook POST to Slack, PagerDuty, or a custom URL when
  a new vulnerability is detected or error counts exceed a threshold.

- [ ] **Remote error reporting**
  Opt-in batched POST of error events to a configurable endpoint
  (Sentry-compatible DSN or the guard cloud service), enabling
  cross-instance error correlation.

- [ ] **LLM-powered fix suggestions**
  For errors that match no static pattern in `guard/advisor.py`, optionally
  call a locally-running or remote LLM (Ollama, OpenAI, Anthropic — opt-in,
  never on by default) to generate a free-form suggestion.  The public
  interface remains identical: callers always get a plain string or `None`.

- [ ] **Historical trend analysis**
  Persist error counts to SQLite and expose a `guard report` command that
  shows error frequency trends over the last N days.

- [ ] **AI-workflow integration**
  Attach guard suggestions to the IDE diagnostic channel so AI assistants
  (GitHub Copilot, Cursor, etc.) can auto-fix flagged errors.  Generate a
  `.guard` context file for AI agents and expose guard as a Model Context
  Protocol (MCP) tool server.

---

## Contributing

When implementing a feature from this roadmap:

1. Open a PR referencing the phase and item (e.g., `Phase 2 — thread exception coverage`).
2. Add or update the relevant module docstring's **Current phase** /
   **Next phases** sections.
3. Mark the item `✅` in this file once the PR is merged.

See [`README.md`](README.md) for project setup and testing instructions.
