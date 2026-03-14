"""Tests for guard.__main__ — CLI entry point (guard audit)."""
import json
import sys
from unittest.mock import patch

import pytest

from guard.__main__ import main


# ---------------------------------------------------------------------------
# guard audit — no vulnerabilities
# ---------------------------------------------------------------------------

def test_audit_clean_exit_zero(capsys):
    with patch("guard.__main__.run_all_scans", return_value=[]):
        code = main(["audit"])
    assert code == 0
    captured = capsys.readouterr()
    assert "no vulnerabilities" in captured.err.lower()


# ---------------------------------------------------------------------------
# guard audit — with vulnerabilities
# ---------------------------------------------------------------------------

def test_audit_findings_exit_nonzero(capsys):
    warnings = [
        "⚠️  Detected vulnerable dependency: pyyaml==5.1.0 — CVE-2020-14343",
    ]
    with patch("guard.__main__.run_all_scans", return_value=warnings):
        code = main(["audit"])
    assert code == 1
    captured = capsys.readouterr()
    assert "pyyaml" in captured.err
    assert "1 finding(s)" in captured.err


# ---------------------------------------------------------------------------
# guard audit --json
# ---------------------------------------------------------------------------

def test_audit_json_output(capsys):
    warnings = [
        "⚠️  Detected vulnerable dependency: requests==2.19.0 — CVE-XYZ",
    ]
    with patch("guard.__main__.run_all_scans", return_value=warnings):
        code = main(["audit", "--json"])
    assert code == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["vulnerabilities"] == 1
    assert len(data["findings"]) == 1
    assert "requests" in data["findings"][0]


def test_audit_json_clean(capsys):
    with patch("guard.__main__.run_all_scans", return_value=[]):
        code = main(["audit", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["vulnerabilities"] == 0
    assert data["findings"] == []


# ---------------------------------------------------------------------------
# guard audit --broken
# ---------------------------------------------------------------------------

def test_audit_broken_flag():
    with patch("guard.__main__.run_all_scans", return_value=[]) as mock_scan:
        main(["audit", "--broken"])
    mock_scan.assert_called_once_with(check_broken=True)


# ---------------------------------------------------------------------------
# guard (no command) — prints help
# ---------------------------------------------------------------------------

def test_no_command_prints_help(capsys):
    code = main([])
    assert code == 0


# ---------------------------------------------------------------------------
# python -m guard invocation
# ---------------------------------------------------------------------------

def test_module_invocation():
    """Verify the __main__.py can be found via python -m guard."""
    import importlib
    mod = importlib.import_module("guard.__main__")
    assert hasattr(mod, "main")
