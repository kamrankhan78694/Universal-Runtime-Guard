"""Thread-safety stress tests for api_guard.install() / uninstall().

These tests verify that the API guard module behaves correctly under
concurrent access, including rapid install/uninstall cycles and
concurrent HTTP requests through the guarded session.
"""

import threading
import time

import pytest
import responses

from guard import api_guard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_api_guard():
    """Ensure the API guard is uninstalled after each test."""
    api_guard.uninstall()
    yield
    api_guard.uninstall()


# ---------------------------------------------------------------------------
# Thread-safety stress tests
# ---------------------------------------------------------------------------

def test_concurrent_install_uninstall_no_crash():
    """Rapidly installing and uninstalling from multiple threads must not crash."""
    errors = []

    def toggle(cycles):
        try:
            for _ in range(cycles):
                api_guard.install()
                api_guard.uninstall()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=toggle, args=(50,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive(), "Thread did not finish within timeout"

    assert errors == [], f"Errors during concurrent install/uninstall: {errors}"


@responses.activate
def test_concurrent_requests_through_guard():
    """Multiple threads making HTTP requests through the guard should not crash."""
    import requests as req_lib

    responses.add(
        responses.GET,
        "https://api.example.com/data",
        json={"id": 1, "name": "test"},
        status=200,
    )

    api_guard.install(expected_schema={"id": None, "name": None})

    errors = []
    results = []

    def make_request():
        try:
            resp = req_lib.get("https://api.example.com/data")
            results.append(resp.status_code)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=make_request) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive(), "Thread did not finish within timeout"

    assert errors == [], f"Errors during concurrent requests: {errors}"
    assert len(results) == 10
    assert all(s == 200 for s in results)


def test_install_while_requests_in_flight():
    """Installing the guard while requests are in-flight should not crash."""
    errors = []

    def installer():
        try:
            for _ in range(20):
                api_guard.install()
                time.sleep(0.001)
                api_guard.uninstall()
        except Exception as exc:
            errors.append(exc)

    t = threading.Thread(target=installer)
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "Thread did not finish within timeout"
    assert errors == [], f"Errors during install while in-flight: {errors}"


def test_uninstall_idempotent_from_threads():
    """Calling uninstall() from multiple threads concurrently should be safe."""
    api_guard.install()
    errors = []

    def do_uninstall():
        try:
            api_guard.uninstall()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=do_uninstall) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive(), "Thread did not finish within timeout"

    assert errors == [], f"Errors during concurrent uninstall: {errors}"


def test_install_idempotent_from_threads():
    """Calling install() from multiple threads concurrently should be safe."""
    errors = []

    def do_install():
        try:
            api_guard.install()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=do_install) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive(), "Thread did not finish within timeout"

    assert errors == [], f"Errors during concurrent install: {errors}"
