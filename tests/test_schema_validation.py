"""Tests for Phase 2 API guard features — type-aware and nested schema validation."""
import json
from unittest.mock import MagicMock

import pytest

from guard.api_guard import _GuardedResponse, _validate_schema


# ---------------------------------------------------------------------------
# Helpers
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


# ---------------------------------------------------------------------------
# Type-aware schema validation
# ---------------------------------------------------------------------------

def test_type_schema_correct_types_no_warning(capsys):
    resp = _mock_response(
        200,
        {"Content-Type": "application/json"},
        '{"id": 42, "name": "Alice"}',
    )
    _GuardedResponse(resp, expected_schema={"id": int, "name": str})
    captured = capsys.readouterr()
    assert captured.err == ""


def test_type_schema_wrong_type_warns(capsys):
    resp = _mock_response(
        200,
        {"Content-Type": "application/json"},
        '{"id": "not_an_int", "name": "Alice"}',
    )
    _GuardedResponse(resp, expected_schema={"id": int, "name": str})
    captured = capsys.readouterr()
    assert "wrong type" in captured.err.lower()
    assert "id" in captured.err
    assert "int" in captured.err
    assert "str" in captured.err


def test_type_schema_none_value_accepts_any(capsys):
    """Schema value of None should only check key presence (Phase 1 compat)."""
    resp = _mock_response(
        200,
        {"Content-Type": "application/json"},
        '{"id": 42, "name": "Alice"}',
    )
    _GuardedResponse(resp, expected_schema={"id": None, "name": None})
    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Nested schema validation
# ---------------------------------------------------------------------------

def test_nested_dict_schema_valid_no_warning(capsys):
    body = json.dumps({"user": {"id": 1, "name": "Bob"}})
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    _GuardedResponse(
        resp,
        expected_schema={"user": {"id": int, "name": str}},
    )
    captured = capsys.readouterr()
    assert captured.err == ""


def test_nested_dict_schema_wrong_type_warns(capsys):
    body = json.dumps({"user": {"id": "bad", "name": "Bob"}})
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    _GuardedResponse(
        resp,
        expected_schema={"user": {"id": int, "name": str}},
    )
    captured = capsys.readouterr()
    assert "wrong type" in captured.err.lower()
    assert "user.id" in captured.err


def test_nested_dict_schema_missing_key(capsys):
    body = json.dumps({"user": {"name": "Bob"}})
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    _GuardedResponse(
        resp,
        expected_schema={"user": {"id": int, "name": str}},
    )
    captured = capsys.readouterr()
    assert "missing" in captured.err.lower()
    assert "user.id" in captured.err


# ---------------------------------------------------------------------------
# List schema validation
# ---------------------------------------------------------------------------

def test_list_schema_valid_no_warning(capsys):
    body = json.dumps({"users": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]})
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    _GuardedResponse(
        resp,
        expected_schema={"users": [{"id": int, "name": str}]},
    )
    captured = capsys.readouterr()
    assert captured.err == ""


def test_list_schema_wrong_item_type_warns(capsys):
    body = json.dumps({"users": [{"id": "bad", "name": "A"}]})
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    _GuardedResponse(
        resp,
        expected_schema={"users": [{"id": int, "name": str}]},
    )
    captured = capsys.readouterr()
    assert "wrong type" in captured.err.lower()


def test_list_schema_not_a_list_warns(capsys):
    body = json.dumps({"users": "not_a_list"})
    resp = _mock_response(200, {"Content-Type": "application/json"}, body)
    _GuardedResponse(
        resp,
        expected_schema={"users": [{"id": int, "name": str}]},
    )
    captured = capsys.readouterr()
    assert "wrong type" in captured.err.lower()
    assert "list" in captured.err


# ---------------------------------------------------------------------------
# _validate_schema standalone
# ---------------------------------------------------------------------------

def test_validate_schema_top_level_type():
    """Top-level type check."""
    warnings = []
    import guard.api_guard as ag
    orig_warn = ag._warn
    ag._warn = lambda msg: warnings.append(msg)
    try:
        _validate_schema("hello", int, "http://test.com")
        assert len(warnings) == 1
        assert "wrong type" in warnings[0].lower()
    finally:
        ag._warn = orig_warn


def test_validate_schema_dict_expected_but_got_other():
    """Expecting a dict but got a non-dict."""
    warnings = []
    import guard.api_guard as ag
    orig_warn = ag._warn
    ag._warn = lambda msg: warnings.append(msg)
    try:
        _validate_schema("not a dict", {"key": int}, "http://test.com")
        assert len(warnings) == 1
        assert "wrong type" in warnings[0].lower()
    finally:
        ag._warn = orig_warn
