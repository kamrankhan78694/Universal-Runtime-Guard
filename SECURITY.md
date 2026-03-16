# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | ✅ Current          |
| 0.2.x   | ⚠️ Security fixes only |
| < 0.2   | ❌ End of life       |

## Reporting a Vulnerability

If you discover a security vulnerability in Universal Runtime Guard, please
report it responsibly:

1. **Do NOT open a public issue.**

2. **Email the maintainers** with the following details:
   - A description of the vulnerability
   - Steps to reproduce it
   - The impact (e.g., denial of service, code execution, data exposure)
   - Your suggested fix (if any)

3. **Expected response time:**
   - Acknowledgement within 48 hours
   - Initial assessment within 7 days
   - Fix released within 30 days for critical issues

## Security Design Principles

Universal Runtime Guard follows these security principles:

### Defence in depth

- **No mandatory runtime dependencies.** The attack surface is minimal.
- **Input validation.** All public API parameters are type-checked before use.
- **Output sanitisation.** HTTP response bodies are stripped of dangerous
  control characters before reaching application code.
- **Defensive error handling.** The guard's own hooks never crash the host
  application — all internal errors are caught and suppressed silently.

### Thread safety

- Error counts are protected by `threading.Lock` for safe concurrent access.
- `api_guard.install()` and `api_guard.uninstall()` are lock-protected.
- `error_handler.install()` and `error_handler.uninstall()` are lock-protected.

### Supply-chain safety

- Zero mandatory dependencies reduces supply-chain risk.
- The built-in advisory database flags known-vulnerable packages at startup.
- Blocked-package detection warns about known-malicious packages.

## Scope

The following are **in scope** for security reports:

- Vulnerabilities in the `guard` Python package
- Vulnerabilities in the `guard-core` Rust crate
- Bypass of input validation or output sanitisation
- Thread-safety issues that could lead to data corruption
- Denial of service via crafted inputs

The following are **out of scope**:

- Vulnerabilities in dependencies (report to the upstream project)
- Issues that require physical access to the machine
- Social engineering attacks
