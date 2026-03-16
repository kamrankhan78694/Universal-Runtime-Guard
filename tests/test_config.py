"""Tests for guard.config — configuration file loading."""
import os
import tempfile
from pathlib import Path

import pytest

from guard.config import _resolve_type_strings, load_config


# ---------------------------------------------------------------------------
# _resolve_type_strings
# ---------------------------------------------------------------------------

def test_resolve_type_strings_basic():
    schema = {"id": "int", "name": "str", "score": "float"}
    result = _resolve_type_strings(schema)
    assert result == {"id": int, "name": str, "score": float}


def test_resolve_type_strings_nested():
    schema = {"user": {"id": "int", "name": "str"}}
    result = _resolve_type_strings(schema)
    assert result == {"user": {"id": int, "name": str}}


def test_resolve_type_strings_unknown_passthrough():
    schema = {"x": "unknown_type", "y": 42}
    result = _resolve_type_strings(schema)
    assert result == {"x": "unknown_type", "y": 42}


# ---------------------------------------------------------------------------
# load_config — guard.toml
# ---------------------------------------------------------------------------

def test_load_config_guard_toml():
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "guard.toml"
        toml_path.write_text(
            'check_dependencies = false\n'
            'guard_api = true\n'
            'auto_patch = true\n'
            'verbose = false\n'
            'structured_logging = true\n'
        )
        config = load_config(directory=tmpdir)
        assert config["check_dependencies"] is False
        assert config["guard_api"] is True
        assert config["auto_patch"] is True
        assert config["verbose"] is False
        assert config["structured_logging"] is True


def test_load_config_guard_toml_with_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "guard.toml"
        toml_path.write_text(
            '[expected_api_schema]\n'
            'id = "int"\n'
            'name = "str"\n'
        )
        config = load_config(directory=tmpdir)
        assert config["expected_api_schema"] == {"id": int, "name": str}


# ---------------------------------------------------------------------------
# load_config — pyproject.toml [tool.guard]
# ---------------------------------------------------------------------------

def test_load_config_pyproject_toml():
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "pyproject.toml"
        toml_path.write_text(
            '[tool.guard]\n'
            'guard_errors = false\n'
            'check_broken = true\n'
        )
        config = load_config(directory=tmpdir)
        assert config["guard_errors"] is False
        assert config["check_broken"] is True


# ---------------------------------------------------------------------------
# load_config — no config file
# ---------------------------------------------------------------------------

def test_load_config_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(directory=tmpdir)
        assert config == {}


# ---------------------------------------------------------------------------
# load_config — guard.toml takes priority over pyproject.toml
# ---------------------------------------------------------------------------

def test_load_config_guard_toml_priority():
    with tempfile.TemporaryDirectory() as tmpdir:
        guard_toml = Path(tmpdir) / "guard.toml"
        guard_toml.write_text('verbose = false\n')
        pyproject_toml = Path(tmpdir) / "pyproject.toml"
        pyproject_toml.write_text(
            '[tool.guard]\n'
            'verbose = true\n'
        )
        config = load_config(directory=tmpdir)
        # guard.toml should take priority
        assert config["verbose"] is False


# ---------------------------------------------------------------------------
# B-5: malformed TOML must warn, not silently drop
# ---------------------------------------------------------------------------

def test_load_config_malformed_toml_warns():
    """Malformed TOML should emit a warning and return empty config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "guard.toml"
        toml_path.write_text("this is not valid TOML [[[[")

        import warnings as _warnings

        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            config = load_config(directory=tmpdir)

        assert config == {}
        assert any("malformed TOML" in str(w.message) for w in caught)


def test_load_config_valid_toml_no_warning():
    """Valid TOML should load without any warnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "guard.toml"
        toml_path.write_text('verbose = true\n')

        import warnings as _warnings

        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            config = load_config(directory=tmpdir)

        assert config["verbose"] is True
        assert not any("malformed TOML" in str(w.message) for w in caught)
