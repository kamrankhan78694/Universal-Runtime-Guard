"""Tests for Phase 2 error handler features — threading and asyncio coverage."""
import asyncio
import sys
import threading
import time

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
# Threading excepthook
# ---------------------------------------------------------------------------

def test_threading_excepthook_installed():
    """install() should replace threading.excepthook."""
    original = threading.excepthook
    error_handler.install(auto_patch=True)
    assert threading.excepthook is not original
    assert threading.excepthook.__name__ == "_guard_threading_excepthook"


def test_threading_excepthook_restored():
    """uninstall() should restore the original threading.excepthook."""
    original = threading.excepthook
    error_handler.install(auto_patch=True)
    error_handler.uninstall()
    assert threading.excepthook is original


def test_thread_exception_counted(capsys):
    """Exceptions in worker threads should be counted."""
    error_handler.install(auto_patch=True)

    def worker():
        raise RuntimeError("thread boom")

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5)

    counts = error_handler.error_counts()
    assert counts.get("RuntimeError", 0) >= 1


def test_thread_exception_report(capsys):
    """Exceptions in worker threads should produce a rich report."""
    error_handler.install(auto_patch=True)

    def worker():
        raise ValueError("thread test error")

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5)

    captured = capsys.readouterr()
    assert "ValueError" in captured.err
    assert "Universal Runtime Guard" in captured.err
    assert "thread" in captured.err.lower()


# ---------------------------------------------------------------------------
# Asyncio exception handler
# ---------------------------------------------------------------------------

def test_asyncio_exception_handler():
    """Asyncio tasks with unhandled exceptions should be counted."""
    error_handler.install(auto_patch=True)

    async def failing_task():
        raise RuntimeError("async boom")

    async def run():
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(error_handler._guard_async_exception_handler)
        task = asyncio.create_task(failing_task())
        # Give the task time to fail
        await asyncio.sleep(0.1)
        # Force exception retrieval
        try:
            await task
        except RuntimeError:
            pass

    # The task will raise, but the exception handler should have been called
    # with the context before we await it.
    error_handler.reset_counts()

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(error_handler._guard_async_exception_handler)

    async def _run():
        task = loop.create_task(failing_task())
        await asyncio.sleep(0.1)

    loop.run_until_complete(_run())
    loop.close()

    counts = error_handler.error_counts()
    assert counts.get("RuntimeError", 0) >= 1


def test_asyncio_exception_handler_report(capsys):
    """Asyncio exception handler should produce a rich report."""
    error_handler.install(auto_patch=True)

    async def failing_task():
        raise ValueError("async test error")

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(error_handler._guard_async_exception_handler)

    async def _run():
        task = loop.create_task(failing_task())
        await asyncio.sleep(0.1)

    loop.run_until_complete(_run())
    loop.close()

    captured = capsys.readouterr()
    assert "ValueError" in captured.err
    assert "Universal Runtime Guard" in captured.err
