# Universal Runtime Guard

[![CI](https://github.com/kamrankhan78694/Universal-Runtime-Guard/actions/workflows/ci.yml/badge.svg)](https://github.com/kamrankhan78694/Universal-Runtime-Guard/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **A single dependency that automatically prevents crashes, security exploits,
> and bad API responses in production.**

```python
import guard
guard.activate()
```

That one call turns on three independent protection layers:

| Layer | What it does |
|-------|-------------|
| **Dependency scanner** | Warns about known-vulnerable or blocked packages at start-up |
| **API guard** | Validates and sanitises every `requests` HTTP response automatically |
| **Error handler** | Enriches every unhandled exception with a rich report and an actionable fix suggestion |

---

## Installation

```bash
pip install universal-runtime-guard
```

> **Python ≥ 3.8 required.**  No mandatory runtime dependencies.
> `requests` is patched automatically *if it is installed*, but it is not required.

For configuration file support (`guard.toml`) on Python < 3.11, install with:

```bash
pip install universal-runtime-guard[toml]
```

Python 3.11+ includes `tomllib` in the standard library and does not need
the extra.

---

## Quick start

```python
import guard

guard.activate()
# 🛡️  Universal Runtime Guard activated — layers: dependency scanner, API guard, error handler
```

From this point on:

- Any installed package matching a known CVE prints a `⚠️` warning to *stderr*.
- Every `requests.get/post/…` response is validated; schema mismatches and
  non-2xx status codes print a `⚠️` warning.
- Any unhandled exception prints a rich traceback *plus* a `💡 Suggestion` line
  before the process exits.

---

## What you see in practice

### Dependency warning

```
⚠️  Detected vulnerable dependency: pyyaml==5.1.0 — CVE-2020-14343: Arbitrary code execution via yaml.load().
```

### API schema mismatch

```
⚠️  Detected API schema mismatch: response from https://api.example.com/users
    is missing expected keys: ['email']
```

### Enriched error report

```
────────────────────────────────────────────────────────────
🛡️  Universal Runtime Guard — Unhandled ZeroDivisionError
────────────────────────────────────────────────────────────
Traceback (most recent call last):
  File "app.py", line 12, in compute
    return total / count
ZeroDivisionError: division by zero

💡 Suggestion [ZeroDivisionError]: You are dividing by zero.
   Guard the divisor with an `if divisor != 0` check.
────────────────────────────────────────────────────────────
```

---

## API reference

### `guard.activate(**kwargs)`

Activate all (or selected) protection layers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `check_dependencies` | `bool` | `True` | Scan installed packages for CVEs and blocked packages |
| `check_broken` | `bool` | `False` | Also try to import every installed package to detect broken ones (slower) |
| `guard_api` | `bool` | `True` | Monkey-patch `requests` to validate and sanitise responses |
| `expected_api_schema` | `dict \| None` | `None` | Schema describing expected JSON API response structure; supports type checking (`int`, `str`, …), nested dicts, and list-of-object schemas (`[{…}]`) |
| `guard_errors` | `bool` | `True` | Install enriched `sys.excepthook`, `threading.excepthook`, and asyncio exception handler |
| `auto_patch` | `bool` | `False` | Suppress (instead of re-raise) non-fatal unhandled exceptions — use only in long-running services |
| `verbose` | `bool` | `True` | Print the startup banner |
| `structured_logging` | `bool` | `False` | Emit guard events as structured JSON log records to *stderr* |
| `config_dir` | `str \| None` | `None` | Directory to search for `guard.toml` or `pyproject.toml`; defaults to cwd |

### `guard.deactivate()`

Remove all guard hooks.  Useful in tests or interactive sessions.

### `guard.error_counts() -> dict[str, int]`

Return the number of unhandled exceptions recorded per exception type since
the last `reset_counts()` call.

```python
>>> guard.error_counts()
{'ZeroDivisionError': 3, 'KeyError': 1}
```

### `guard.reset_counts()`

Clear all recorded error counts.

### `guard.__version__`

Current release version string (e.g. `"0.1.0"`).

---

## Selective layer activation

```python
import guard

# Only the dependency scanner — no HTTP or error patching.
guard.activate(guard_api=False, guard_errors=False)

# Only the error handler — useful when you manage HTTP yourself.
guard.activate(check_dependencies=False, guard_api=False)

# API guard with a type-aware response schema.
guard.activate(
    check_dependencies=False,
    guard_errors=False,
    expected_api_schema={"id": int, "name": str, "email": str},
)

# Nested and list schemas for complex API responses.
guard.activate(
    check_dependencies=False,
    guard_errors=False,
    expected_api_schema={
        "users": [{"id": int, "name": str}],
        "meta": {"total": int, "page": int},
    },
)
```

---

## Configuration file

Guard settings can be loaded from a `guard.toml` file or a `[tool.guard]`
section in `pyproject.toml`, so teams can version-control their configuration
without changing application code.

```toml
# guard.toml
check_dependencies = true
check_broken = false
guard_api = true
guard_errors = true
auto_patch = false
verbose = true

[expected_api_schema]
id = "int"
name = "str"
```

Or in `pyproject.toml`:

```toml
[tool.guard]
check_dependencies = true
guard_errors = true
auto_patch = true

[tool.guard.expected_api_schema]
id = "int"
name = "str"
```

Then just call `guard.activate()` — settings are picked up automatically.

---

## CLI: `guard audit`

Scan installed dependencies and exit non-zero when vulnerabilities are found.
Ideal for CI/CD pipelines.

```bash
# Human-readable output
python -m guard audit

# Include broken-import check (slower)
python -m guard audit --broken

# JSON output for machine consumption
python -m guard audit --json
```

Example output:

```
⚠️  Detected vulnerable dependency: pyyaml==5.1.0 — CVE-2020-14343

🛡️  guard audit: 1 finding(s) detected.
```

---

## Structured logging

Enable structured JSON logging for integration with log aggregators
(Datadog, Loki, CloudWatch):

```python
import guard
guard.activate(structured_logging=True)
```

Each guard event is emitted as a single-line JSON record to *stderr*:

```json
{"timestamp": "2025-01-15 10:30:00,123", "level": "WARNING", "logger": "guard", "message": "⚠️  ...", "event": "dependency_warning"}
```

---

## Using the API guard directly

```python
from guard.api_guard import install, uninstall

install(expected_schema={"id": int, "name": str})

import requests
r = requests.get("https://api.example.com/user/1")

# r behaves exactly like a normal requests.Response, plus:
data = r.json()            # control characters stripped automatically
text = r.sanitized_text()  # same for raw text responses

uninstall()  # restore original requests.Session.send
```

---

## Using the error handler directly

```python
from guard.error_handler import install, uninstall, error_counts, reset_counts

install(auto_patch=True)   # suppress crashes, keep running
# … run application …
print(error_counts())      # {'ConnectionError': 2}
reset_counts()
uninstall()
```

---

## Using the dependency scanner directly

```python
from guard.dependency import run_all_scans

warnings = run_all_scans(check_broken=True)
for w in warnings:
    print(w)
```

---

## Development

```bash
git clone https://github.com/kamrankhan78694/Universal-Runtime-Guard.git
cd Universal-Runtime-Guard
pip install -e ".[dev]"
pytest
```

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for the full multi-phase roadmap,
including planned features and contribution guidelines.

---

## Architecture

Universal Runtime Guard follows a **Rust-core, polyglot-wrapper** design:

```
              guard-core  (Rust crate)
        ┌───────┬───────┬───────┬──────────┐
        │Python │Node.js│  Go   │ Rust/WASM│
        │(PyO3) │(napi) │(cgo)  │ (native) │
        └───────┴───────┴───────┴──────────┘
```

- **Python is the front door** — the largest AI developer community, the
  fastest feedback loop, the first package shipped.
- **Rust is the engine room** — deterministic performance, memory-safe, and
  compiles to native binaries for every platform.
- Each ecosystem gets an idiomatic wrapper published through its own package
  manager (`pip`, `npm`, `go get`, `cargo`).

Phase 2 (current) extends guard with configuration file support, type-aware
and nested schema validation, thread/async exception coverage, a `guard audit`
CLI command, and structured JSON logging.  Phase 3 will port the internals
to Rust and replace them with PyO3 bindings — the public Python API stays
identical.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design document.

---

## Roadmap summary

| Phase | Status | Highlights |
|-------|--------|-----------|
| **1 — Core Python package** | ✅ shipped | Static CVE DB · requests patch · heuristic advisor |
| **2 — Config & deeper coverage** | ✅ shipped | `guard.toml` · type-aware schema · threads/async · `guard audit` CLI · structured logging |
| **3 — Rust core & multi-language** | 📋 planned | Rust engine · PyO3 binding · Node.js/Go wrappers |
| **4 — Live advisory DB** | 🔭 future | OSV live feed · SBOM export · licence scanning |
| **5 — Dashboard & LLM** | 🔭 future | Prometheus metrics · alert webhooks · AI-workflow integration |

---

## Contributing

We welcome contributions! See [`CONTRIBUTING.md`](CONTRIBUTING.md) for
development setup, coding standards, and the PR process.

For a detailed list of changes in each release, see
[`CHANGELOG.md`](CHANGELOG.md).

---

## License

[MIT](LICENSE)

