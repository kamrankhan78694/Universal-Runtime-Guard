"""Tests for guard.advisor — fix suggestion engine."""
import pytest

from guard.advisor import suggest


class _E(Exception):
    pass


def _exc(exc_type, message):
    """Helper: return (type, instance) for use with suggest()."""
    try:
        raise exc_type(message)
    except exc_type as e:
        return exc_type, e


# ---------------------------------------------------------------------------
# Import / module errors
# ---------------------------------------------------------------------------

def test_suggest_no_module():
    t, e = _exc(ModuleNotFoundError, "No module named 'nonexistent_pkg'")
    result = suggest(t, e)
    assert result is not None
    assert "pip install nonexistent_pkg" in result


def test_suggest_cannot_import_name():
    t, e = _exc(ImportError, "cannot import name 'OldClass' from 'mylib'")
    result = suggest(t, e)
    assert result is not None
    assert "OldClass" in result
    assert "mylib" in result


# ---------------------------------------------------------------------------
# Attribute errors
# ---------------------------------------------------------------------------

def test_suggest_attribute_error():
    t, e = _exc(AttributeError, "'NoneType' object has no attribute 'split'")
    result = suggest(t, e)
    assert result is not None
    assert "NoneType" in result
    assert "split" in result


# ---------------------------------------------------------------------------
# Type errors
# ---------------------------------------------------------------------------

def test_suggest_not_callable():
    t, e = _exc(TypeError, "'int' object is not callable")
    result = suggest(t, e)
    assert result is not None
    assert "int" in result


# ---------------------------------------------------------------------------
# Key / Index errors
# ---------------------------------------------------------------------------

def test_suggest_key_error():
    t, e = _exc(KeyError, "'missing_key'")
    result = suggest(t, e)
    assert result is not None
    assert ".get()" in result


def test_suggest_index_error():
    t, e = _exc(IndexError, "list index out of range")
    result = suggest(t, e)
    assert result is not None
    assert "length" in result.lower() or "index" in result.lower()


# ---------------------------------------------------------------------------
# Zero division
# ---------------------------------------------------------------------------

def test_suggest_zero_division():
    t, e = _exc(ZeroDivisionError, "division by zero")
    result = suggest(t, e)
    assert result is not None
    assert "zero" in result.lower()


# ---------------------------------------------------------------------------
# File errors
# ---------------------------------------------------------------------------

def test_suggest_file_not_found():
    t, e = _exc(FileNotFoundError, "No such file or directory: '/tmp/missing.txt'")
    result = suggest(t, e)
    assert result is not None
    assert "/tmp/missing.txt" in result


# ---------------------------------------------------------------------------
# No match → None
# ---------------------------------------------------------------------------

def test_suggest_returns_none_for_unknown():
    t, e = _exc(RuntimeError, "some completely unknown error message xyz")
    result = suggest(t, e)
    assert result is None
