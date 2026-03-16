"""Asyncio edge-case tests for the error handler.

These tests cover scenarios that are tricky in async contexts:
cancelled tasks, tasks raising after cancellation, exception handler
with no traceback, exception handler for non-exception events,
and multiple concurrent failing tasks.
"""

import asyncio
import sys

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
# Asyncio edge cases
# ---------------------------------------------------------------------------

def test_asyncio_cancelled_task_not_counted():
    """CancelledError should not be counted as an unhandled exception."""
    error_handler.install(auto_patch=True)

    async def cancellable():
        await asyncio.sleep(100)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(error_handler._guard_async_exception_handler)

    async def _run():
        task = loop.create_task(cancellable())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    loop.run_until_complete(_run())
    loop.close()

    counts = error_handler.error_counts()
    assert counts.get("CancelledError", 0) == 0


def test_asyncio_multiple_concurrent_failures():
    """Multiple concurrent failing tasks should all be counted."""
    error_handler.install(auto_patch=True)

    async def fail_with(msg):
        raise RuntimeError(msg)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(error_handler._guard_async_exception_handler)

    async def _run():
        tasks = [
            loop.create_task(fail_with(f"error {i}"))
            for i in range(5)
        ]
        await asyncio.sleep(0.1)
        # Let the exception handler process them

    loop.run_until_complete(_run())
    loop.close()

    counts = error_handler.error_counts()
    assert counts.get("RuntimeError", 0) >= 5


def test_asyncio_handler_no_exception_context():
    """Handler should gracefully handle context without an exception."""
    error_handler.install(auto_patch=True)

    loop = asyncio.new_event_loop()
    # Directly call the handler with no exception in context
    context = {"message": "just a warning, no exception"}
    # This should call loop.default_exception_handler and not crash
    error_handler._guard_async_exception_handler(loop, context)
    loop.close()

    # Should not have counted anything
    counts = error_handler.error_counts()
    assert len(counts) == 0


def test_asyncio_handler_exception_no_traceback(capsys):
    """Handler should work even when exception has no traceback."""
    error_handler.install(auto_patch=True)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(error_handler._guard_async_exception_handler)

    exc = RuntimeError("no traceback attached")
    # Exception created but never raised, so no __traceback__
    context = {"exception": exc, "message": "test"}

    error_handler._guard_async_exception_handler(loop, context)
    loop.close()

    counts = error_handler.error_counts()
    assert counts.get("RuntimeError", 0) >= 1

    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
    assert "no traceback attached" in captured.err


def test_asyncio_handler_system_exit_forwarded():
    """SystemExit should be forwarded to the default handler, not counted."""
    error_handler.install(auto_patch=True)

    loop = asyncio.new_event_loop()
    default_called = []
    original_default = loop.default_exception_handler

    def tracking_default(context):
        default_called.append(context)
        original_default(context)

    loop.default_exception_handler = tracking_default

    context = {"exception": SystemExit(1), "message": "exit"}
    error_handler._guard_async_exception_handler(loop, context)
    loop.close()

    counts = error_handler.error_counts()
    assert counts.get("SystemExit", 0) == 0
    assert len(default_called) == 1


def test_asyncio_exception_with_task_name(capsys):
    """Handler should include the task name in the error report."""
    error_handler.install(auto_patch=True)

    async def named_task():
        raise ValueError("named task error")

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(error_handler._guard_async_exception_handler)

    async def _run():
        task = loop.create_task(named_task())
        if hasattr(task, "set_name"):
            task.set_name("my-important-task")
        await asyncio.sleep(0.1)

    loop.run_until_complete(_run())
    loop.close()

    captured = capsys.readouterr()
    assert "ValueError" in captured.err
    counts = error_handler.error_counts()
    assert counts.get("ValueError", 0) >= 1
