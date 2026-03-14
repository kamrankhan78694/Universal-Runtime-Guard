# Architecture

Universal Runtime Guard follows a **Rust-core, polyglot-wrapper** architecture.
The design mirrors projects like SQLite, ripgrep, and Deno: a single,
high-performance core written in a systems language with thin idiomatic
wrappers published through each ecosystem's native package manager.

---

## Why this architecture?

A "universal" dependency must sit **below languages**, closer to the machine.
Python is the ideal *front door* — the largest AI developer community lives
there, and prototyping is fastest — but a runtime guard meant to embed inside
many stacks benefits from **predictable performance, small binaries, and easy
embedding**.  Rust delivers all three while remaining memory-safe.

The strategic pattern:

> **Build the core once (Rust) → expose it everywhere → let each ecosystem
> think it's "native."**

---

## Layer diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Developer code                       │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Python  │  Node.js │   Go    │   Rust   │  WASM /     │
│  wrapper │  wrapper │  wrapper│  (native)│  Edge       │
│  (PyO3)  │  (napi)  │  (cgo)  │          │             │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│                                                         │
│              guard-core  (Rust crate)                   │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ Vulnerability│ │   API        │ │  Error handler   │ │
│  │ scanner      │ │   sanitiser  │ │  + advisor       │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Advisory database (embedded)           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Component breakdown

### `guard-core` (Rust crate)

The shared engine.  Contains all logic that must be identical across
languages:

| Subsystem | Responsibility |
|-----------|---------------|
| **Vulnerability scanner** | Match installed packages against the advisory DB |
| **Advisory database** | Embedded, versioned snapshot of CVE / OSV data; optional live-fetch layer |
| **API sanitiser** | Strip control characters; validate JSON schema; check status codes |
| **Error advisor** | Pattern-match exception messages to fix suggestions |
| **SBOM generator** | Produce CycloneDX / SPDX output from scan results |

Compiles to:
- A native shared library (`.so` / `.dylib` / `.dll`) for Python (via PyO3)
  and Go (via cgo).
- A native Node.js addon (via napi-rs).
- A WASM module for edge/browser environments.
- A standalone CLI binary (`guard audit`, `guard sbom`).

### Language wrappers

Each wrapper is a thin, idiomatic shim that:

1. Loads the compiled `guard-core` binary for the current platform.
2. Hooks into the runtime's error-handling and HTTP primitives.
3. Re-exports a single `activate()` entry point.

| Wrapper | Hook points | Package manager |
|---------|------------|-----------------|
| **Python** | `sys.excepthook`, `requests.Session.send`, `pkg_resources` | `pip` |
| **Node.js** | `process.on('uncaughtException')`, `node-fetch` / `axios` patch | `npm` |
| **Go** | `recover()`, `net/http.DefaultClient` middleware | `go get` |
| **Rust** | Direct crate dependency; `panic` hook; `reqwest` middleware | `cargo` |

---

## Current state vs. target

```
Phase 1 (now)          Target architecture
─────────────          ───────────────────

 Python only            guard-core (Rust)
 ┌────────────┐         ┌────────────────────────┐
 │ guard/*.py  │   →    │ guard-core (Rust crate) │
 │ (pure Python│        ├────────┬───────┬────────┤
 │  prototype) │        │ Python │ Node  │ Go … │
 └────────────┘         └────────┴───────┴────────┘
```

Phase 1 (the current pure-Python implementation) serves as the **prototype
and specification**.  Every behaviour codified in the Python tests becomes a
contract that the Rust core must satisfy.  The migration path:

1. **Phase 1 ✅** — Ship the Python prototype; acquire early adopters.
2. **Phase 2** — Harden the Python package (config files, async, threads).
3. **Phase 3** — Port core logic to Rust; replace Python internals with
   PyO3 bindings; ship Node.js + Go wrappers.
4. **Phase 4** — Live advisory DB, SBOM, supply-chain tooling.
5. **Phase 5** — Dashboard, alerting, LLM suggestions.

Python remains the *front door*: the easiest install, the largest community,
the fastest feedback loop.  Rust is the *engine room*: deterministic
performance, a single source of truth, and effortless cross-platform
distribution.

---

## AI-workflow integration (future)

The most viral dependencies attach themselves to the **largest developer
habit**.  Today that habit is AI-assisted coding (GitHub Copilot, ChatGPT,
Cursor, etc.).  A dependency that quietly plugs into AI-assisted workflows
could spread faster than traditional libraries by riding the same behavioural
current.

Planned integration points:

| Integration | Description |
|------------|-------------|
| **Copilot-aware error context** | Attach guard suggestions to the IDE diagnostic channel so Copilot can auto-fix flagged errors |
| **`.guard` context file** | Generate a project-level context file that AI assistants can read to understand the dependency health posture |
| **MCP tool server** | Expose guard's scanner and advisor as a Model Context Protocol tool so AI agents can invoke them directly |

---

## Directory structure (target)

```
Universal-Runtime-Guard/
├── guard-core/              # Rust workspace root
│   ├── Cargo.toml
│   ├── src/                 # Core engine (scanner, sanitiser, advisor)
│   └── tests/
├── bindings/
│   ├── python/              # PyO3 wrapper → publishes to PyPI
│   │   ├── guard/           # Python-idiomatic API (activate / deactivate)
│   │   └── pyproject.toml
│   ├── node/                # napi-rs wrapper → publishes to npm
│   │   ├── src/
│   │   └── package.json
│   └── go/                  # cgo wrapper → Go module
│       ├── guard.go
│       └── go.mod
├── cli/                     # Standalone CLI binary (guard audit / guard sbom)
│   ├── Cargo.toml
│   └── src/main.rs
├── ARCHITECTURE.md          # ← you are here
├── DEVELOPMENT.md           # Phase-by-phase roadmap
├── README.md
└── LICENSE
```

---

## References

Architectural precedents that inform this design:

- **SQLite** — C core, bindings for every language.
- **ripgrep** — Rust core, used as a library inside VS Code.
- **Deno** — Rust core, JavaScript/TypeScript front-end.
- **Ruff** — Rust core, Python CLI wrapper, replaces flake8/black/isort.
- **Docker** — Go core, CLI + API for every platform.

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for the detailed implementation
roadmap.
