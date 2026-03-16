"""Tests for production hardening: thread-safe counts, input validation,
structured logging integration, and defensive error handling.
"""

import asyncio
import json
import sys
import threading
import time

import pytest

from guard import api_guard, error_handler
from guard import logging as guard_logging
from guard.core import activate, deactivate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state():
    """Reset all guard state between tests."""
    deactivate()
    error_handler.reset_counts()
    yield
    deactivate()
    error_handler.reset_counts()


# ---------------------------------------------------------------------------
# Thread-safe error counts
# ---------------------------------------------------------------------------

def test_error_counts_thread_safe():
    """Error counts should be accurate under concurrent access."""
    error_handler.install(auto_patch=True)
    errors_per_thread = 20
    num_threads = 5

    def raise_errors():
        for _ in range(errors_per_thread):
            try:
                raise RuntimeError("thread-safe test")
            except RuntimeError:
                exc_type, exc_value, exc_tb = sys.exc_info()
                error_handler._guard_excepthook(exc_type, exc_value, exc_tb)

    threads = [threading.Thread(target=raise_errors) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive()

    counts = error_handler.error_counts()
    assert counts["RuntimeError"] == errors_per_thread * num_threads


def test_error_counts_returns_copy():
    """error_counts() should return a copy, not the internal dict."""
    error_handler.install(auto_patch=True)
    try:
        raise ValueError("test")
    except ValueError:
        error_handler._guard_excepthook(*sys.exc_info())

    counts = error_handler.error_counts()
    counts["ValueError"] = 999  # Mutating the copy
    assert error_handler.error_counts()["ValueError"] == 1


def test_reset_counts_thread_safe():
    """reset_counts() should be safe to call from any thread."""
    error_handler.install(auto_patch=True)
    try:
        raise RuntimeError("test")
    except RuntimeError:
        error_handler._guard_excepthook(*sys.exc_info())

    assert error_handler.error_counts().get("RuntimeError", 0) >= 1

    errors = []
    def reset_from_thread():
        try:
            error_handler.reset_counts()
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=reset_from_thread)
    t.start()
    t.join(timeout=5)
    assert errors == []
    assert error_handler.error_counts() == {}


# ---------------------------------------------------------------------------
# Input validation on activate()
# ---------------------------------------------------------------------------

def test_activate_rejects_non_dict_schema():
    """activate() should raise TypeError for non-dict expected_api_schema."""
    with pytest.raises(TypeError, match="expected_api_schema must be a dict"):
        activate(
            expected_api_schema="not a dict",
            check_dependencies=False,
            guard_api=False,
            guard_errors=False,
            verbose=False,
        )


def test_activate_rejects_non_str_config_dir():
    """activate() should raise TypeError for non-str config_dir."""
    with pytest.raises(TypeError, match="config_dir must be a str"):
        activate(
            config_dir=123,
            check_dependencies=False,
            guard_api=False,
            guard_errors=False,
            verbose=False,
        )


def test_activate_accepts_none_schema():
    """activate() should accept None as expected_api_schema."""
    activate(
        expected_api_schema=None,
        check_dependencies=False,
        guard_api=True,
        guard_errors=False,
        verbose=False,
    )
    # Should not raise


def test_activate_accepts_dict_schema():
    """activate() should accept a dict as expected_api_schema."""
    activate(
        expected_api_schema={"id": int, "name": str},
        check_dependencies=False,
        guard_api=True,
        guard_errors=False,
        verbose=False,
    )
    # Should not raise


# ---------------------------------------------------------------------------
# Structured logging integration
# ---------------------------------------------------------------------------

def test_error_handler_emits_structured_log():
    """Error handler should emit structured log events when logging is enabled."""
    import io
    import logging as _logging

    # Capture logging output via a custom handler
    capture_stream = io.StringIO()
    guard_logging.enable()

    # Add a temporary handler that writes to our capture stream
    capture_handler = _logging.StreamHandler(capture_stream)
    from guard.logging import _JsonFormatter
    capture_handler.setFormatter(_JsonFormatter())
    logger = _logging.getLogger("guard")
    logger.addHandler(capture_handler)

    error_handler.install(auto_patch=True)

    try:
        raise ValueError("structured log test")
    except ValueError:
        error_handler._guard_excepthook(*sys.exc_info())

    logger.removeHandler(capture_handler)
    guard_logging.disable()

    output = capture_stream.getvalue()
    log_lines = [
        line for line in output.split("\n")
        if line.strip().startswith("{")
    ]
    assert len(log_lines) >= 1
    log_data = json.loads(log_lines[0])
    assert log_data["event"] == "unhandled_exception"
    assert log_data["data"]["exception_type"] == "ValueError"


def test_api_guard_emits_structured_log(capsys):
    """API guard warnings should emit structured log events when enabled."""
    import responses as resp_mock

    guard_logging.enable()

    resp_mock.start()
    try:
        resp_mock.add(
            resp_mock.GET,
            "https://api.example.com/test",
            json={"id": 1},
            status=500,
        )

        api_guard.install()
        import requests
        requests.get("https://api.example.com/test")
    finally:
        api_guard.uninstall()
        resp_mock.stop()
        resp_mock.reset()
        guard_logging.disable()

    captured = capsys.readouterr()
    log_lines = [
        line for line in captured.err.split("\n")
        if line.strip().startswith("{")
    ]
    assert len(log_lines) >= 1
    found_api_warning = any(
        json.loads(l).get("event") == "api_warning"
        for l in log_lines
    )
    assert found_api_warning


# ---------------------------------------------------------------------------
# Defensive error handling — guard must never crash the application
# ---------------------------------------------------------------------------

def test_error_handler_survives_broken_advisor(monkeypatch):
    """If advisor.suggest() crashes, the error handler should still work."""
    error_handler.install(auto_patch=True)

    def broken_suggest(*args, **kwargs):
        raise RuntimeError("advisor is broken")

    from guard import advisor
    monkeypatch.setattr(advisor, "suggest", broken_suggest)

    # This should NOT raise, even though the advisor is broken
    try:
        raise ValueError("test with broken advisor")
    except ValueError:
        # Calling the hook directly should not crash
        error_handler._guard_excepthook(*sys.exc_info())

    counts = error_handler.error_counts()
    assert counts.get("ValueError", 0) >= 1


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_is_0_3_0():
    """Version should be updated to 0.3.0."""
    import guard
    assert guard.__version__ == "0.3.0"
