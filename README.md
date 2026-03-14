# Universal Runtime Guard

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
| `expected_api_schema` | `dict \| None` | `None` | Keys the JSON API response must contain (values are ignored in Phase 1); extra/missing keys trigger a warning |
| `guard_errors` | `bool` | `True` | Install the enriched `sys.excepthook` |
| `auto_patch` | `bool` | `False` | Suppress (instead of re-raise) non-fatal unhandled exceptions — use only in long-running services |
| `verbose` | `bool` | `True` | Print the startup banner |

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

# API guard with an expected response schema.
guard.activate(
    check_dependencies=False,
    guard_errors=False,
    expected_api_schema={"id": None, "name": None, "email": None},
)
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

## Roadmap summary

| Phase | Status | Highlights |
|-------|--------|-----------|
| **1 — Core Python package** | ✅ shipped | Static CVE DB · requests patch · heuristic advisor |
| **2 — Config & deeper coverage** | 📋 planned | `guard.toml` · type-aware schema · threads/async |
| **3 — Multi-language & CI/CD** | 📋 planned | Rust core · Node.js/Go shims · `guard audit` CLI |
| **4 — Live advisory DB** | 🔭 future | OSV live feed · SBOM export · licence scanning |
| **5 — Dashboard & LLM** | 🔭 future | Prometheus metrics · alert webhooks · LLM suggestions |

---

## License

[MIT](LICENSE)

