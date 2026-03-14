"""Tests for guard.core — the activate() / deactivate() integration."""
import sys
from unittest.mock import patch

import pytest

import guard
from guard import api_guard, error_handler
from guard.core import activate, deactivate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state():
    """Reset all guard state before and after every test."""
    api_guard.uninstall()
    error_handler.uninstall()
    error_handler.reset_counts()
    yield
    api_guard.uninstall()
    error_handler.uninstall()
    error_handler.reset_counts()


# ---------------------------------------------------------------------------
# activate()
# ---------------------------------------------------------------------------

def test_activate_prints_banner(capsys):
    with patch("guard.dependency.run_all_scans", return_value=[]):
        activate()
    captured = capsys.readouterr()
    assert "Universal Runtime Guard activated" in captured.err
    assert "🛡️" in captured.err


def test_activate_installs_error_handler():
    original = sys.excepthook
    with patch("guard.dependency.run_all_scans", return_value=[]):
        activate(guard_api=False)
    assert sys.excepthook is not original


def test_activate_dependency_warnings_printed(capsys):
    fake_warnings = ["⚠️  Detected vulnerable dependency: requests==2.19.0 — CVE-XYZ"]
    with patch("guard.dependency.run_all_scans", return_value=fake_warnings):
        activate(guard_api=False, guard_errors=False)
    captured = capsys.readouterr()
    assert "requests" in captured.err
    assert "CVE-XYZ" in captured.err


def test_activate_no_check_dependencies(capsys):
    with patch("guard.dependency.run_all_scans", return_value=[]) as mock_scan:
        activate(check_dependencies=False, guard_api=False, guard_errors=False, verbose=False)
    mock_scan.assert_not_called()


def test_activate_verbose_false_no_banner(capsys):
    with patch("guard.dependency.run_all_scans", return_value=[]):
        activate(verbose=False)
    captured = capsys.readouterr()
    assert "Universal Runtime Guard activated" not in captured.err


def test_activate_installs_api_guard():
    try:
        import requests  # noqa: F401
    except ImportError:
        pytest.skip("requests not installed")

    import requests

    original = requests.Session.send
    with patch("guard.dependency.run_all_scans", return_value=[]):
        activate(guard_errors=False)
    assert requests.Session.send is not original


# ---------------------------------------------------------------------------
# deactivate()
# ---------------------------------------------------------------------------

def test_deactivate_uninstalls_error_handler():
    with patch("guard.dependency.run_all_scans", return_value=[]):
        activate(guard_api=False)
    assert sys.excepthook.__name__ == "_guard_excepthook"
    deactivate()
    assert sys.excepthook.__name__ != "_guard_excepthook"


def test_deactivate_uninstalls_api_guard():
    try:
        import requests  # noqa: F401
    except ImportError:
        pytest.skip("requests not installed")

    import requests

    original = requests.Session.send
    with patch("guard.dependency.run_all_scans", return_value=[]):
        activate(guard_errors=False)
    deactivate()
    assert requests.Session.send is original


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def test_public_api_exports():
    assert callable(guard.activate)
    assert callable(guard.deactivate)
    assert callable(guard.error_counts)
    assert callable(guard.reset_counts)
    assert hasattr(guard, "__version__")
