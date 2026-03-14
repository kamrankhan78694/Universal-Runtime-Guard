# Outstanding Work & Known Issues

This document tracks known bugs, missing features, test coverage gaps, and
planned improvements for Universal Runtime Guard.  Items are grouped by
severity and tagged with the relevant source file so they are easy to find.

> **Legend:**  🔴 Bug · 🟡 Improvement · 🟢 Enhancement · 🧪 Test gap

---

## Bugs

### 🔴 B-1: Asyncio exception handler is defined but never auto-installed

**File:** `guard/error_handler.py` (lines 248–272)

`_guard_async_exception_handler()` is fully implemented, but `install()` only
sets `sys.excepthook` and `threading.excepthook`.  No code registers the
asyncio handler on an event loop, so uncaught exceptions in async tasks are
**not** intercepted despite the module docstring (lines 5–7, 42–45) claiming
otherwise.

The existing tests (`tests/test_threading_async.py`) manually call
`loop.set_exception_handler(...)`, which masks the gap.

**Impact:** Users who call `guard.activate()` and rely on async coverage get
no protection for asyncio tasks.

**Suggested fix:** Either auto-install the handler (e.g. by monkey-patching
`asyncio.new_event_loop()`) or update the docstring and README to document
that manual registration is required.

---

### 🔴 B-2: `_error_counts` updates are not thread-safe

**File:** `guard/error_handler.py` (lines 110, 154, 205)

The global `_error_counts` dictionary is updated with a non-atomic
read-modify-write:

```python
_error_counts[type_name] = _error_counts.get(type_name, 0) + 1
```

When multiple threads or asyncio tasks raise exceptions concurrently, count
updates can be lost (classic "lost update" race condition).

**Impact:** `guard.error_counts()` returns inaccurate values in multi-threaded
or async applications.

**Suggested fix:** Protect updates with a `threading.Lock`.

---

### 🔴 B-3: Race condition in `api_guard.install()` / `uninstall()`

**File:** `guard/api_guard.py` (lines 284–316)

`install()` and `uninstall()` use a non-atomic check-then-act pattern on the
`_installed` flag.  If two threads call `install()` concurrently, the second
thread may overwrite `_original_send` with the already-patched version,
making `uninstall()` restore the wrong function.

The module docstring (lines 35–36) documents that these functions are not
thread-safe, but the code still lacks any defensive guard.

**Suggested fix:** Add a `threading.Lock` around the install/uninstall blocks,
or use an `if _installed` + `return` pattern under the lock.

---

### 🔴 B-4: `scan_broken()` uses a fragile module-name heuristic

**File:** `guard/dependency.py` (line 169)

```python
top_level = pkg.key.replace("-", "_")
```

Many packages have a top-level module name that differs from their
distribution name (e.g. `pillow` → `PIL`, `pyyaml` → `yaml`,
`beautifulsoup4` → `bs4`).  These are incorrectly flagged as broken.

**Impact:** False-positive "broken dependency" warnings when
`check_broken=True`.

**Suggested fix:** Use the `top_level.txt` metadata entry
(`pkg.get_metadata('top_level.txt')`) when available, and fall back to the
current heuristic only when it is not.

---

### 🔴 B-5: `config.py` silently swallows TOML parse errors

**File:** `guard/config.py` (line 119)

```python
except Exception:
    return {}
```

A malformed `guard.toml` is silently ignored instead of warning the user.
This makes configuration typos invisible.

**Impact:** Users think their config is applied when it is actually silently
dropped.

**Suggested fix:** Catch only `FileNotFoundError` / `IsADirectoryError`.  Let
TOML decode errors propagate (or emit a warning).

---

## Improvements

### 🟡 I-1: `__version__` missing from `__all__`

**File:** `guard/__init__.py` (line 63)

`__version__` is documented as part of the public API (lines 33–37) but is
not listed in `__all__`, so wildcard imports (`from guard import *`) and
tools that inspect `__all__` do not expose it.

**Suggested fix:** Add `"__version__"` to `__all__`.

---

### 🟡 I-2: Invalid type strings in config silently pass through

**File:** `guard/config.py` (lines 89–99)

When `expected_api_schema` contains an unknown type string (e.g. `"tuple"`),
it is kept as a raw string and later silently skipped during schema
validation (because `isinstance(schema, type)` is `False` for a string).

**Impact:** Misconfigured schemas offer no protection, and the user receives
no feedback.

**Suggested fix:** Emit a warning (or raise) for unrecognised type names in
`_resolve_type_strings()`.

---

### 🟡 I-3: `uninstall()` does not restore asyncio exception handlers

**File:** `guard/error_handler.py` (lines 275–285)

Because the asyncio handler is never auto-installed (B-1), `uninstall()` also
does not restore it.  If asyncio support is added later, `uninstall()` will
need to be updated in parallel.

---

### 🟡 I-4: Error hooks do not protect against their own exceptions

**File:** `guard/error_handler.py` (lines 97–241)

If `advisor.suggest()` or `traceback.format_exception()` raises an exception
inside the hook, it will propagate uncaught.  Exception hooks should be
wrapped in a defensive `try/except` to avoid cascading failures.

**Suggested fix:** Wrap the hook body in `try: ... except Exception: ...`
that falls back to the original hook.

---

### 🟡 I-5: CLI returns exit code 0 when no subcommand is given

**File:** `guard/__main__.py` (lines 65–67)

Running `python -m guard` with no arguments prints help and returns 0.
CLI convention expects a non-zero exit code when a required subcommand is
missing.

**Suggested fix:** Return 1 when no command is provided.

---

### 🟡 I-6: `_GuardedResponse.json()` does not handle malformed JSON consistently

**File:** `guard/api_guard.py` (lines 249–252)

During `__init__`, `_validate_json()` catches JSON decode errors and emits a
warning.  But when the user later calls `.json()`, the raw
`self._response.json()` can raise the same exception unguarded.  This creates
an inconsistency between the guard's validation (lenient) and the caller's
experience (strict).

**Suggested fix:** Either document this as intentional ("the warning fires
once; the caller is responsible for catching `ValueError`"), or wrap
`.json()` similarly.

---

### 🟡 I-7: Vulnerability DB uses prefix matching instead of semver

**File:** `guard/dependency.py` (line 143)

```python
if any(version.startswith(prefix) for prefix in affected_prefixes):
```

While the current advisory entries use sufficiently specific prefixes, the
approach is inherently fragile.  A prefix like `"2."` would match all 2.x
versions, causing false positives.

**Suggested fix:** Adopt a semver-range comparison (e.g.
`packaging.version.Version`) once the project adds `packaging` as an optional
dependency.

---

## Enhancements (Phase 2 follow-ups)

### 🟢 E-1: `_validate_schema()` does not validate the schema itself

**File:** `guard/api_guard.py` (lines 99–179)

If a user passes a malformed schema (e.g. `{"users": [123]}` or nested
lists), the code silently accepts it without warning.

**Suggested fix:** Add a schema-shape validation step in `install()` or at
the top of `_validate_schema()`.

---

### 🟢 E-2: `_GuardedResponse.sanitized_text()` and `__repr__` are untested

**File:** `guard/api_guard.py` (lines 254–266)

No test exercises `sanitized_text()` or `__repr__`.  These are public or
semi-public methods that should have at least one test each.

---

### 🟢 E-3: HTTP redirect status codes (3xx) are untested

**File:** `tests/test_api_guard.py`

`_check_status()` handles 3xx responses, but no test verifies the warning
message for 301, 302, 307, etc.

---

## Test Coverage Gaps

### 🧪 T-1: `advisor.py` — 15 of 24 suggestion patterns untested

**Patterns with no test coverage:**

| Pattern | Description |
|---------|-------------|
| `unsupported operand type` | Type mismatch in arithmetic |
| `object is not iterable/subscriptable` | Not callable/iterable |
| `invalid literal for int()` | Value conversion |
| `Permission denied` | File permission |
| `Connection refused` | Network |
| `getaddrinfo failed` | DNS resolution |
| `timed out` | Timeout |
| `maximum recursion depth exceeded` | Recursion |
| `MemoryError` | Out of memory |
| `SSL` errors | Certificate issues |
| `Expecting value: line ...` | JSON parse errors |

---

### 🧪 T-2: `dependency.py` — `scan_broken()` has no dedicated test

The function contains complex import logic, module-name heuristics, and
multiple exception-handling paths — all untested.

---

### 🧪 T-3: `config.py` — malformed TOML and error paths untested

- `_load_toml()` `except Exception` branch is never exercised.
- `tomllib` vs `tomli` fallback path is not covered.
- Unknown type strings in schema are not tested.

---

### 🧪 T-4: `error_handler.py` — threading and asyncio edge cases

- `SystemExit` / `KeyboardInterrupt` in threads: not tested.
- Asyncio handler with `context["exception"] = None`: not tested.
- `auto_patch=True` suppression in threads and asyncio: not tested.

---

### 🧪 T-5: `core.py` — parameter interactions and re-activation

- `check_broken=True` path through `activate()`: not tested.
- Calling `activate()` after `deactivate()`: not tested.
- Invalid `config_dir` value: not tested.

---

## Phase 3 roadmap items (from DEVELOPMENT.md)

These are documented in `DEVELOPMENT.md` but listed here for completeness:

- [ ] `guard-core` Rust crate
- [ ] Python PyO3 binding (replace pure-Python internals)
- [ ] Node.js wrapper (napi-rs)
- [ ] Go module (cgo)
- [ ] GitHub Actions reusable workflow
- [ ] Pre-commit hook

See `DEVELOPMENT.md` for Phases 4 and 5.
