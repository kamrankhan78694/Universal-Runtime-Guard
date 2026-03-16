"""
dependency.py — Broken and vulnerable dependency detection.

Overview
--------
This module scans the currently installed Python packages and emits warning
strings for any package that:

* matches a known-vulnerable version in the built-in advisory database
  (:func:`scan_vulnerabilities`), or
* appears on the unconditional block-list (:func:`scan_blocked`), or
* is installed but fails to import, indicating a broken environment
  (:func:`scan_broken` — disabled by default due to import latency).

All three scans are combined by :func:`run_all_scans`, which is the function
called by :func:`guard.core.activate`.

Advisory database design
~~~~~~~~~~~~~~~~~~~~~~~~
The built-in :data:`_VULNERABILITY_DB` maps lowercase package names to a list
of ``(affected_version_prefixes, advisory_text)`` tuples.  Version matching
is performed with a simple ``version.startswith(prefix)`` check so the module
remains dependency-free.

For production deployments a richer source is recommended — see **Phase 2**
below.

Current phase
-------------
**Phase 1 — Static, built-in advisory database** (shipped).
A curated dictionary of well-known CVEs is bundled with the package.  No
network calls are made; scans run in microseconds.

Next phases
-----------
**Phase 2 — Live OSV / PyPA Advisory DB integration** (planned).
Add an *optional* async or cached HTTP fetch of
``https://osv.dev/query`` so the database stays current without requiring
a package upgrade.  Network calls will be opt-in (``live=True`` flag on
:func:`run_all_scans`) and will fall back gracefully to the built-in
database when offline.

**Phase 3 — SBOM generation** (planned).
Export a CycloneDX or SPDX Software Bill of Materials from the scan
results so teams can integrate guard into their supply-chain tooling.

**Phase 4 — Dependency graph conflict detection** (future).
Use ``pip``'s resolver internals to surface version-conflict trees, not
just individual package advisories.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Curated vulnerability database (package → set of affected version prefixes)
# ---------------------------------------------------------------------------
# Each entry maps a package name (lowercase, as returned by pkg_resources) to
# a list of (affected_versions_set_or_prefix, advisory_message) tuples.
# "affected" is checked with a simple `version.startswith(prefix)` guard so
# we keep this dependency-free.  For production use you would replace this
# with a live OSV / PyPA Advisory DB query.

_VULNERABILITY_DB: dict[str, list[tuple[list[str], str]]] = {
    "requests": [
        (["2.19.", "2.20."], "CVE-2018-18074: Redirect stripping credentials."),
    ],
    "urllib3": [
        (["1.24.", "1.25."], "CVE-2019-11324: Certificate validation bypass."),
        (["1.26.0", "1.26.1", "1.26.2", "1.26.3", "1.26.4"],
         "CVE-2021-33503: Catastrophic ReDoS in URL parsing."),
    ],
    "pyyaml": [
        (["3.", "4.", "5.0.", "5.1.", "5.2.", "5.3."],
         "CVE-2020-14343: Arbitrary code execution via yaml.load()."),
    ],
    "pillow": [
        (["8.0.", "8.1.", "8.2."],
         "CVE-2021-25293: Buffer overflow in SGI RLE decoding."),
    ],
    "django": [
        (["2.0.", "2.1."],
         "CVE-2019-14232: Catastrophic ReDoS in strip_tags()."),
        (["3.0.", "3.1."],
         "CVE-2021-33203: Path traversal via admindocs."),
    ],
    "flask": [
        (["0.", "1.0.", "1.1."],
         "GHSA-562c-5r94-xh97: Open redirect in flask.redirect()."),
    ],
    "cryptography": [
        (["3.3.", "3.4."],
         "CVE-2023-23931: Bleichenbacher oracle in RSA PKCS#1 v1.5."),
    ],
    "paramiko": [
        (["2.9.", "2.10.", "2.11."],
         "CVE-2022-24302: Race condition in key-file creation."),
    ],
    "setuptools": [
        (["65.0.", "65.1.", "65.2.", "65.3.", "65.4.", "65.5."],
         "CVE-2022-40897: ReDoS in package_index."),
    ],
    "sqlalchemy": [
        (["1.3."],
         "Advisory: SQL injection risk when using raw string literals."),
    ],
}

# Packages that are entirely unsafe to use regardless of version.
_BLOCKED_PACKAGES: dict[str, str] = {
    "insecure-package": "This package is flagged as unconditionally insecure.",
    "malicious-package": "This package has been identified as malicious.",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _installed_packages() -> dict[str, str]:
    """Return {name_lower: version} for all packages visible to pkg_resources."""
    try:
        import pkg_resources  # noqa: PLC0415
        return {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    except Exception:
        return {}


def scan_vulnerabilities() -> Iterator[str]:
    """
    Yield warning strings for every installed package that matches a known
    vulnerable version in the built-in advisory database.
    """
    packages = _installed_packages()
    for pkg_name, advisories in _VULNERABILITY_DB.items():
        version = packages.get(pkg_name)
        if version is None:
            continue
        for affected_prefixes, advisory in advisories:
            if any(version.startswith(prefix) for prefix in affected_prefixes):
                yield (
                    f"⚠️  Detected vulnerable dependency: {pkg_name}=={version} "
                    f"— {advisory}"
                )


def scan_blocked() -> Iterator[str]:
    """Yield warning strings for installed packages that are unconditionally blocked."""
    packages = _installed_packages()
    for pkg_name, reason in _BLOCKED_PACKAGES.items():
        if pkg_name in packages:
            yield f"🚫 Blocked insecure package detected: {pkg_name} — {reason}"


def _get_top_level_names(pkg: Any) -> list[str]:
    """Return the importable top-level module names for a distribution.

    Uses the ``top_level.txt`` metadata file (written by setuptools/pip at
    install time) to obtain the *real* module names.  Falls back to
    guessing from the distribution name when metadata is unavailable.
    """
    try:
        text = pkg.get_metadata("top_level.txt")
        names = [n.strip() for n in text.strip().splitlines() if n.strip()]
        if names:
            return names
    except (FileNotFoundError, KeyError, AttributeError, ValueError, IOError):
        pass
    return [pkg.key.replace("-", "_")]


def scan_broken() -> Iterator[str]:
    """
    Yield warning strings for packages that are installed but fail to import,
    which usually indicates a broken or conflicting installation.
    """
    try:
        import pkg_resources  # noqa: PLC0415
        for pkg in pkg_resources.working_set:
            try:
                names = _get_top_level_names(pkg)
                last_import_err: Exception | None = None
                for name in names:
                    if name in sys.modules:
                        break
                    try:
                        importlib.import_module(name)
                        break
                    except ImportError as exc:
                        last_import_err = exc
                        continue
                    except Exception:
                        # Other errors (e.g., syntax errors) — package exists
                        # but has issues; don't flag as missing.
                        break
                else:
                    # None of the top-level names were importable.
                    if last_import_err is not None:
                        yield (
                            f"⚠️  Detected broken dependency: "
                            f"{pkg.key}=={pkg.version} — {last_import_err}"
                        )
            except Exception:
                pass
    except Exception:
        pass


def run_all_scans(*, check_broken: bool = False) -> list[str]:
    """
    Run vulnerability and blocked-package scans.

    *check_broken* is ``False`` by default because importing every installed
    package has noticeable latency; enable it when you want a thorough audit.
    """
    warnings: list[str] = []
    warnings.extend(scan_vulnerabilities())
    warnings.extend(scan_blocked())
    if check_broken:
        warnings.extend(scan_broken())
    return warnings
