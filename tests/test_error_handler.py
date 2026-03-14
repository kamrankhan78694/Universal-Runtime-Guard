"""Tests for guard.error_handler — runtime error catching and reporting."""
import sys
from io import StringIO

import pytest

from guard import error_handler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_handler():
    """Ensure the handler is uninstalled and counts are reset after each test."""
    error_handler.uninstall()
    error_handler.reset_counts()
    yield
    error_handler.uninstall()
    error_handler.reset_counts()


# ---------------------------------------------------------------------------
# install / uninstall
# ---------------------------------------------------------------------------

def test_install_replaces_excepthook():
    original = sys.excepthook
    error_handler.install()
    assert sys.excepthook is not original
    assert sys.excepthook.__name__ == "_guard_excepthook"


def test_uninstall_restores_excepthook():
    original = sys.excepthook
    error_handler.install()
    error_handler.uninstall()
    assert sys.excepthook is original


def test_install_is_idempotent():
    error_handler.install()
    hook_after_first = sys.excepthook
    error_handler.install()
    assert sys.excepthook is hook_after_first


# ---------------------------------------------------------------------------
# Hook behaviour
# ---------------------------------------------------------------------------

def test_hook_outputs_error_report(capsys):
    error_handler.install(auto_patch=True)

    try:
        raise ValueError("test error message")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_value, exc_tb)

    captured = capsys.readouterr()
    assert "ValueError" in captured.err
    assert "Universal Runtime Guard" in captured.err


def test_hook_includes_suggestion_for_known_error(capsys):
    error_handler.install(auto_patch=True)

    try:
        raise ZeroDivisionError("division by zero")
    except ZeroDivisionError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_value, exc_tb)

    captured = capsys.readouterr()
    assert "💡" in captured.err
    assert "zero" in captured.err.lower()


def test_hook_tracks_error_counts():
    error_handler.install(auto_patch=True)

    for _ in range(3):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_tb)

    counts = error_handler.error_counts()
    assert counts.get("RuntimeError") == 3


def test_hook_system_exit_not_suppressed():
    """SystemExit must bypass the guard hook."""
    error_handler.install(auto_patch=True)

    original_hook = error_handler._original_excepthook
    called = []

    def fake_original(t, v, tb):
        called.append(t)

    error_handler._original_excepthook = fake_original
    try:
        exc_type = SystemExit
        exc_value = SystemExit(0)
        sys.excepthook(exc_type, exc_value, None)
    finally:
        error_handler._original_excepthook = original_hook

    assert SystemExit in called


# ---------------------------------------------------------------------------
# error_counts / reset_counts
# ---------------------------------------------------------------------------

def test_reset_counts_clears_state():
    error_handler.install(auto_patch=True)

    try:
        raise KeyError("k")
    except KeyError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_value, exc_tb)

    assert error_handler.error_counts().get("KeyError") == 1
    error_handler.reset_counts()
    assert error_handler.error_counts() == {}
