# Contributing to Universal Runtime Guard

Thank you for your interest in contributing! This document explains how to
set up a development environment, run the test suite, and submit changes.

---

## Development Setup

### Prerequisites

- **Python ≥ 3.8** (tested with 3.8 – 3.12)
- **pip** (bundled with Python ≥ 3.4)
- **Git**

### Clone and install

```bash
git clone https://github.com/kamrankhan78694/Universal-Runtime-Guard.git
cd Universal-Runtime-Guard
python -m pip install -e ".[dev]"
```

The `[dev]` extra installs all test and development dependencies:

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |
| `responses` | HTTP response mocking |
| `requests` | HTTP client (optional at runtime, required for tests) |
| `tomli` | TOML parsing (Python < 3.11) |

---

## Running Tests

```bash
# Run the full suite
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=guard --cov-report=term-missing

# Run a single test file
python -m pytest tests/test_core.py -v

# Run a single test
python -m pytest tests/test_core.py::test_activate_prints_banner -v
```

All tests must pass before a PR is merged.

---

## Code Style

- Follow **PEP 8** for formatting.
- Use **PEP 257** docstring conventions (module, class, and public function
  docstrings).
- Keep lines to **88 characters** where practical.
- Prefer **explicit imports** over wildcard imports.
- Every public function must include a docstring with a brief description,
  parameters, and return type.

---

## Project Structure

```
guard/               # Main package
  __init__.py        # Public API exports
  __main__.py        # CLI entry point (guard audit)
  core.py            # activate() / deactivate()
  api_guard.py       # HTTP response validation
  dependency.py      # Vulnerability scanning
  error_handler.py   # Exception hooks
  advisor.py         # Fix suggestions
  config.py          # Configuration file support
  logging.py         # Structured JSON logging

tests/               # Test suite (pytest)
  test_*.py          # One file per module
```

---

## Pull Request Process

1. **Fork and branch.** Create a feature branch from `main`:
   ```bash
   git checkout -b my-feature main
   ```

2. **Make your changes.** Keep commits small and focused.

3. **Add or update tests.** Every new feature or bug fix should include
   corresponding tests.

4. **Run the test suite.** Ensure all tests pass:
   ```bash
   python -m pytest tests/ -v
   ```

5. **Update documentation.** If your change affects the public API, update
   the README and module docstrings.

6. **Open a pull request.** Reference the relevant issue or roadmap item
   (e.g., "Phase 2 — thread exception coverage"). Fill in the PR template.

7. **Respond to review.** A maintainer will review your PR. Please respond
   to feedback promptly.

---

## Issue Guidelines

- **Bug reports:** Use the bug report template. Include reproduction steps,
  expected vs. actual behaviour, and your environment details.
- **Feature requests:** Use the feature request template. Describe the use
  case, proposed solution, and alternatives considered.
- **Questions:** Open a discussion instead of an issue.

---

## Release Process

1. Update version in `pyproject.toml` and `guard/__init__.py`.
2. Add a new section to `CHANGELOG.md`.
3. Update `DEVELOPMENT.md` to mark shipped features.
4. Create a git tag: `git tag v0.X.0`.
5. Push the tag: `git push origin v0.X.0`.
6. CI will build and publish to PyPI automatically.

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold a welcoming and inclusive environment
for everyone.

---

## Questions?

If you're unsure about something, open an issue or reach out to the
maintainers. We're happy to help!
