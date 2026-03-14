"""Tests for guard.logging — structured JSON logging output."""
import json
import logging

import pytest

from guard import logging as guard_logging


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_logging():
    """Ensure logging is disabled before and after each test."""
    guard_logging.disable()
    yield
    guard_logging.disable()


# ---------------------------------------------------------------------------
# enable / disable
# ---------------------------------------------------------------------------

def test_enable_returns_logger():
    logger = guard_logging.enable()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "guard"


def test_is_enabled():
    assert guard_logging.is_enabled() is False
    guard_logging.enable()
    assert guard_logging.is_enabled() is True
    guard_logging.disable()
    assert guard_logging.is_enabled() is False


def test_enable_idempotent():
    logger1 = guard_logging.enable()
    logger2 = guard_logging.enable()
    assert logger1 is logger2


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------

def test_log_event_outputs_json(capsys):
    guard_logging.enable()
    guard_logging.log_event(
        "dependency_warning",
        message="pyyaml is vulnerable",
        package="pyyaml",
        version="5.1.0",
    )
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip())
    assert record["event"] == "dependency_warning"
    assert record["message"] == "pyyaml is vulnerable"
    assert record["data"]["package"] == "pyyaml"
    assert record["data"]["version"] == "5.1.0"
    assert record["logger"] == "guard"
    assert "timestamp" in record


def test_log_event_no_data(capsys):
    guard_logging.enable()
    guard_logging.log_event("test_event", message="hello")
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip())
    assert record["event"] == "test_event"
    assert record["message"] == "hello"
    assert "data" not in record


def test_log_event_disabled_noop(capsys):
    # Logging is disabled by default (via fixture)
    guard_logging.log_event("test_event", message="should not appear")
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""
