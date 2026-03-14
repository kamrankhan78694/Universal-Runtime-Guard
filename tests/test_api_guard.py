"""Tests for guard.api_guard — HTTP response validation and sanitisation."""
import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from guard import api_guard
from guard.api_guard import _GuardedResponse, _sanitize_value


# ---------------------------------------------------------------------------
# _sanitize_value
# ---------------------------------------------------------------------------

def test_sanitize_removes_control_chars():
    assert _sanitize_value("hello\x00world") == "helloworld"
    assert _sanitize_value("tab\there") == "tab\there"   # \t is allowed (0x09)
    assert _sanitize_value("newline\nok") == "newline\nok"  # \n is allowed (0x0a)
    assert _sanitize_value("bell\x07bad") == "bellbad"


def test_sanitize_nested_dict():
    raw = {"key": "val\x01ue", "nested": {"a": "\x02b"}}
    result = _sanitize_value(raw)
    assert result == {"key": "value", "nested": {"a": "b"}}


def test_sanitize_list():
    raw = ["\x00a", "\x01b", "c"]
    assert _sanitize_value(raw) == ["a", "b", "c"]


def test_sanitize_non_string_passthrough():
    assert _sanitize_value(42) == 42
    assert _sanitize_value(3.14) == 3.14
    assert _sanitize_value(None) is None


# ---------------------------------------------------------------------------
# _GuardedResponse
# ---------------------------------------------------------------------------

def _mock_response(
    status_code: int = 200,
    headers: dict | None = None,
    body: str = "",
    url: str = "http://example.com/api",
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.text = body
    resp.url = url
    if body:
        try:
            data = json.loads(body)
            resp.json.return_value = data
        except json.JSONDecodeError:
            resp.json.side_effect = ValueError("No JSON")
    else:
        resp.json.return_value = {}
    return resp


def test_guarded_response_ok_no_warning(capsys):
    resp = _mock_response(200, {"Content-Type": "application/json"}, '{"ok": true}')
    gr = _GuardedResponse(resp)
    captured = capsys.readouterr()
    assert captured.err == ""


def test_guarded_response_warns_on_500(capsys):
    resp = _mock_response(500, {})
    _GuardedResponse(resp)
    captured = capsys.readouterr()
    assert "500" in captured.err
    assert "⚠️" in captured.err


def test_guarded_response_warns_on_404(capsys):
    resp = _mock_response(404, {})
    _GuardedResponse(resp)
    captured = capsys.readouterr()
    assert "404" in captured.err


def test_guarded_response_warns_on_invalid_json(capsys):
    resp = _mock_response(200, {"Content-Type": "application/json"}, "not json")
    resp.json.side_effect = ValueError("No JSON")
    _GuardedResponse(resp)
    captured = capsys.readouterr()
    assert "not valid JSON" in captured.err or "JSON" in captured.err


def test_guarded_response_schema_mismatch_missing_key(capsys):
    resp = _mock_response(200, {"Content-Type": "application/json"}, '{"name": "Alice"}')
    _GuardedResponse(resp, expected_schema={"name": str, "email": str})
    captured = capsys.readouterr()
    assert "missing" in captured.err.lower()
    assert "email" in captured.err


def test_guarded_response_schema_mismatch_extra_key(capsys):
    resp = _mock_response(200, {"Content-Type": "application/json"},
                          '{"name": "Alice", "extra": 1}')
    _GuardedResponse(resp, expected_schema={"name": str})
    captured = capsys.readouterr()
    assert "unexpected" in captured.err.lower()
    assert "extra" in captured.err


def test_guarded_response_json_sanitizes():
    body = '{"msg": "hello\\u0001world"}'
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    resp.json.return_value = {"msg": "hello\x01world"}
    gr = _GuardedResponse(resp)
    result = gr.json()
    assert result["msg"] == "helloworld"


def test_guarded_response_forwards_attributes():
    resp = _mock_response(200)
    resp.custom_attr = "test_value"
    gr = _GuardedResponse(resp)
    assert gr.custom_attr == "test_value"


# ---------------------------------------------------------------------------
# install / uninstall
# ---------------------------------------------------------------------------

def test_install_uninstall_idempotent():
    # Start fresh.
    api_guard.uninstall()

    try:
        import requests  # noqa: F401
    except ImportError:
        pytest.skip("requests not installed")

    import requests

    original = requests.Session.send
    api_guard.install()
    assert requests.Session.send is not original
    patched = requests.Session.send

    # Second install should be a no-op.
    api_guard.install()
    assert requests.Session.send is patched

    api_guard.uninstall()
    assert requests.Session.send is original

    # Second uninstall should be a no-op.
    api_guard.uninstall()
    assert requests.Session.send is original
