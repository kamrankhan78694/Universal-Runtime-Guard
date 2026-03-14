"""Tests for guard.dependency — vulnerability / broken-package scanning."""
import sys
from unittest.mock import MagicMock, patch

import pytest

from guard.dependency import (
    _BLOCKED_PACKAGES,
    _VULNERABILITY_DB,
    run_all_scans,
    scan_blocked,
    scan_vulnerabilities,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pkg(name: str, version: str) -> MagicMock:
    pkg = MagicMock()
    pkg.key = name
    pkg.version = version
    return pkg


def _fake_working_set(packages: list[tuple[str, str]]):
    """Return a mock pkg_resources working_set list."""
    return [_make_pkg(n, v) for n, v in packages]


# ---------------------------------------------------------------------------
# scan_vulnerabilities
# ---------------------------------------------------------------------------

def test_scan_vulnerabilities_detects_known_bad():
    pkgs = [("requests", "2.19.1"), ("urllib3", "1.24.3")]
    with patch("guard.dependency._installed_packages",
               return_value={n: v for n, v in pkgs}):
        warnings = list(scan_vulnerabilities())
    assert any("requests" in w for w in warnings)
    assert any("urllib3" in w for w in warnings)


def test_scan_vulnerabilities_clean():
    pkgs = [("requests", "2.31.0"), ("urllib3", "2.0.4")]
    with patch("guard.dependency._installed_packages",
               return_value={n: v for n, v in pkgs}):
        warnings = list(scan_vulnerabilities())
    assert warnings == []


def test_scan_vulnerabilities_empty_env():
    with patch("guard.dependency._installed_packages", return_value={}):
        warnings = list(scan_vulnerabilities())
    assert warnings == []


def test_scan_vulnerabilities_warning_contains_cve():
    pkgs = [("pyyaml", "5.1.0")]
    with patch("guard.dependency._installed_packages",
               return_value={n: v for n, v in pkgs}):
        warnings = list(scan_vulnerabilities())
    assert len(warnings) == 1
    assert "CVE" in warnings[0] or "Advisory" in warnings[0]
    assert "⚠️" in warnings[0]


# ---------------------------------------------------------------------------
# scan_blocked
# ---------------------------------------------------------------------------

def test_scan_blocked_detects_blocked_package():
    blocked_name = next(iter(_BLOCKED_PACKAGES))
    with patch("guard.dependency._installed_packages",
               return_value={blocked_name: "1.0.0"}):
        warnings = list(scan_blocked())
    assert len(warnings) == 1
    assert "🚫" in warnings[0]
    assert blocked_name in warnings[0]


def test_scan_blocked_no_blocked_installed():
    with patch("guard.dependency._installed_packages",
               return_value={"requests": "2.31.0"}):
        warnings = list(scan_blocked())
    assert warnings == []


# ---------------------------------------------------------------------------
# run_all_scans
# ---------------------------------------------------------------------------

def test_run_all_scans_returns_list():
    with patch("guard.dependency._installed_packages", return_value={}):
        result = run_all_scans()
    assert isinstance(result, list)


def test_run_all_scans_combines_results():
    blocked_name = next(iter(_BLOCKED_PACKAGES))
    pkgs = {blocked_name: "1.0.0", "pyyaml": "5.1.0"}
    with patch("guard.dependency._installed_packages", return_value=pkgs):
        result = run_all_scans()
    # Should include both a vulnerability warning and a blocked warning.
    has_vuln = any("pyyaml" in w for w in result)
    has_blocked = any(blocked_name in w for w in result)
    assert has_vuln
    assert has_blocked
