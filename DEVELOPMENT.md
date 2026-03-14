# Universal Runtime Guard — Development Roadmap

This document tracks the **current development phase** and every planned
future phase for the project.  It is updated as features ship or priorities
change.

---

## Legend

| Symbol | Meaning                    |
|--------|----------------------------|
| ✅     | Shipped in current release |
| 🔄     | In progress                |
| 📋     | Planned (next milestone)   |
| 🔭     | Future (backlog)           |

---

## Phase 1 — Core Python Package ✅ (current)

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

## Phase 2 — Configuration & Deeper Coverage 📋

**Goal:** Let teams configure guard via a file, extend API validation to
types, and cover async / threaded code paths.

### Planned items

- [ ] **`guard.toml` / `pyproject.toml [tool.guard]` support**
  Read settings (which layers to enable, schema paths, auto_patch, etc.)
  from a project config file so developers don't need to change application
  code.

- [ ] **Type-aware API schema validation**
  Extend `api_guard.expected_schema` to accept `{"field": <type>}` and
  validate both presence *and* type of each key.

- [ ] **Nested / list schema validation**
  Support `{"users": [{"id": int, "name": str}]}` schemas for deeply
  nested API responses.

- [ ] **Thread exception coverage**
  Install `threading.excepthook` (Python 3.8+) to catch exceptions in
  worker threads with the same rich reporting.

- [ ] **Asyncio task exception coverage**
  Set a custom `loop.set_exception_handler` so uncaught exceptions in
  async tasks are treated identically to main-thread exceptions.

- [ ] **`guard audit` CLI command**
  A standalone command (`python -m guard audit`) that scans the project's
  `requirements.txt` / `pyproject.toml` and exits non-zero when
  vulnerabilities are found, enabling CI/CD gate-keeping.

- [ ] **Structured logging output**
  Emit errors as JSON log records compatible with `structlog` and
  `logging.handlers` so log aggregators (Datadog, Loki, CloudWatch) can
  index guard events.

---

## Phase 3 — Multi-language & CI/CD Integration 📋

**Goal:** Extend the guard to cover Node.js, Go, and Rust projects and
provide first-class CI/CD integration.

### Planned items

- [ ] **Rust core library**
  Extract the vulnerability-matching and sanitisation logic into a Rust
  crate so it can be compiled as a native extension (`PyO3`) for Python
  and as a WASM module for browser/edge environments.

- [ ] **Node.js shim** (`npm install universal-runtime-guard`)
  A thin JS wrapper around the Rust core that hooks `process.on('uncaughtException')`
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

---

## Contributing

When implementing a feature from this roadmap:

1. Open a PR referencing the phase and item (e.g., `Phase 2 — thread exception coverage`).
2. Add or update the relevant module docstring's **Current phase** /
   **Next phases** sections.
3. Mark the item `✅` in this file once the PR is merged.

See [`README.md`](README.md) for project setup and testing instructions.
