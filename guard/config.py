"""
config.py — Configuration file support for Universal Runtime Guard.

Overview
--------
This module reads guard settings from a project-level configuration file,
allowing teams to version-control their guard configuration without changing
application code.

Configuration is loaded from the *first* source found, in this order:

1. ``guard.toml`` in the current working directory.
2. ``[tool.guard]`` section in ``pyproject.toml`` in the current working
   directory.

If neither file exists, :func:`load_config` returns an empty dictionary
and all parameters fall back to their defaults in :func:`guard.core.activate`.

Supported keys
~~~~~~~~~~~~~~
Every keyword argument accepted by :func:`guard.core.activate` can be
specified in the configuration file:

.. code-block:: toml

    # guard.toml
    check_dependencies = true
    check_broken = false
    guard_api = true
    guard_errors = true
    auto_patch = false
    verbose = true

    [expected_api_schema]
    id = "int"
    name = "str"

Or equivalently in ``pyproject.toml``:

.. code-block:: toml

    [tool.guard]
    check_dependencies = true
    guard_errors = true

    [tool.guard.expected_api_schema]
    id = "int"
    name = "str"

Type strings in ``expected_api_schema`` are mapped to Python built-in types:
``"int"`` → :class:`int`, ``"str"`` → :class:`str`, ``"float"`` → :class:`float`,
``"bool"`` → :class:`bool`, ``"list"`` → :class:`list`, ``"dict"`` → :class:`dict`.

Current phase
-------------
**Phase 2 — Configuration file support** (shipped).
Reads ``guard.toml`` or ``pyproject.toml [tool.guard]`` to configure all
layers without application code changes.

Next phases
-----------
**Phase 3 — Environment variable overrides** (planned).
Allow ``GUARD_*`` environment variables to override config-file settings,
useful for CI and containerised deployments.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Type-string mapping
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, type] = {
    "int": int,
    "str": str,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


def _resolve_type_strings(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert string type names in a schema dict to actual Python types."""
    resolved: dict[str, Any] = {}
    for key, value in schema.items():
        if isinstance(value, str) and value in _TYPE_MAP:
            resolved[key] = _TYPE_MAP[value]
        elif isinstance(value, dict):
            resolved[key] = _resolve_type_strings(value)
        else:
            resolved[key] = value
    return resolved


# ---------------------------------------------------------------------------
# TOML loading
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file, using tomllib (3.11+) or tomli as fallback."""
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            return {}

    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_BOOL_KEYS = frozenset({
    "check_dependencies",
    "check_broken",
    "guard_api",
    "guard_errors",
    "auto_patch",
    "verbose",
})


def load_config(directory: Optional[str] = None) -> dict[str, Any]:
    """
    Load guard configuration from the first available source.

    Parameters
    ----------
    directory:
        Directory to search for config files.  Defaults to the current
        working directory.

    Returns
    -------
    dict
        A dictionary of keyword arguments suitable for passing to
        :func:`guard.core.activate`.  If no config file is found, an
        empty dictionary is returned.
    """
    base = Path(directory) if directory else Path.cwd()

    # 1. guard.toml
    guard_toml = base / "guard.toml"
    if guard_toml.is_file():
        raw = _load_toml(guard_toml)
        return _normalise(raw)

    # 2. pyproject.toml [tool.guard]
    pyproject = base / "pyproject.toml"
    if pyproject.is_file():
        data = _load_toml(pyproject)
        raw = data.get("tool", {}).get("guard", {})
        if raw:
            return _normalise(raw)

    return {}


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert raw TOML data into activate() keyword arguments."""
    result: dict[str, Any] = {}

    for key in _BOOL_KEYS:
        if key in raw:
            result[key] = bool(raw[key])

    if "expected_api_schema" in raw:
        schema = raw["expected_api_schema"]
        if isinstance(schema, dict):
            result["expected_api_schema"] = _resolve_type_strings(schema)

    return result
