"""Unit tests for execution_manager — task registration, cancellation, lifecycle."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest


def _ensure_clean():
    from skiritai.core.execution_manager import _executions
    _executions.clear()


# ============================================================
# 1. register_execution Tests
# ============================================================

class TestRegisterExecution:
    """Test register_execution() and is_running()."""

    def test_register_new_task(self):
        from skiritai.core.execution_manager import register_execution, is_running, _executions

        async def _test():
            _ensure_clean()

            async def dummy():
                await asyncio.sleep(60)

            task = asyncio.create_task(dummy())
            try:
                register_execution("case_a", task)
                assert "case_a" in _executions
                assert is_running("case_a") is True
            finally:
                task.cancel()
                _ensure_clean()

        asyncio.run(_test())

    def test_register_overwrites_existing(self):
        from skiritai.core.execution_manager import register_execution, _executions

        async def _test():
            _ensure_clean()

            async def dummy():
                await asyncio.sleep(60)

            task1 = asyncio.create_task(dummy())
            task2 = asyncio.create_task(dummy())
            try:
                register_execution("case_b", task1)
                register_execution("case_b", task2)
                assert _executions["case_b"] is task2
            finally:
                task1.cancel()
                task2.cancel()
                _ensure_clean()

        asyncio.run(_test())

    def test_is_running_false_for_unknown_case(self):
        from skiritai.core.execution_manager import is_running

        _ensure_clean()
        assert is_running("nonexistent") is False

    def test_is_running_false_for_done_task(self):
        from skiritai.core.execution_manager import register_execution, is_running

        async def _test():
            _ensure_clean()

            async def quick():
                pass

            task = asyncio.create_task(quick())
            register_execution("case_c", task)
            await asyncio.sleep(0.01)  # let it complete
            assert is_running("case_c") is False
            _ensure_clean()

        asyncio.run(_test())


# ============================================================
# 2. cancel_execution Tests
# ============================================================

class TestCancelExecution:
    """Test cancel_execution() behavior."""

    def test_cancel_running_task(self):
        from skiritai.core.execution_manager import register_execution, cancel_execution, _executions

        async def _test():
            _ensure_clean()

            async def dummy():
                await asyncio.sleep(60)

            task = asyncio.create_task(dummy())
            register_execution("case_x", task)

            cancelled = await cancel_execution("case_x")
            assert cancelled is True
            assert "case_x" not in _executions

            # Let cancellation propagate
            try:
                await asyncio.wait_for(task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            _ensure_clean()

        asyncio.run(_test())

    def test_cancel_already_done_task(self):
        from skiritai.core.execution_manager import register_execution, cancel_execution

        async def _test():
            _ensure_clean()

            async def quick():
                pass

            task = asyncio.create_task(quick())
            register_execution("case_y", task)
            await asyncio.sleep(0.01)  # let it complete

            cancelled = await cancel_execution("case_y")
            assert cancelled is False
            _ensure_clean()

        asyncio.run(_test())

    def test_cancel_nonexistent_case(self):
        from skiritai.core.execution_manager import cancel_execution

        async def _test():
            _ensure_clean()
            cancelled = await cancel_execution("does_not_exist")
            assert cancelled is False

        asyncio.run(_test())


# ============================================================
# 3. unregister_execution Tests
# ============================================================

class TestUnregisterExecution:
    """Test unregister_execution()."""

    def test_unregister_existing(self):
        from skiritai.core.execution_manager import register_execution, unregister_execution, _executions

        async def _test():
            _ensure_clean()

            async def dummy():
                await asyncio.sleep(60)

            task = asyncio.create_task(dummy())
            try:
                register_execution("case_z", task)
                assert "case_z" in _executions
                unregister_execution("case_z")
                assert "case_z" not in _executions
            finally:
                task.cancel()
                _ensure_clean()

        asyncio.run(_test())

    def test_unregister_nonexistent_no_error(self):
        from skiritai.core.execution_manager import unregister_execution

        _ensure_clean()
        unregister_execution("does_not_exist")


# ============================================================
# 4. Full Lifecycle Integration Tests
# ============================================================

class TestExecutionLifecycle:
    """Test full register → cancel → unregister lifecycle."""

    def test_full_lifecycle(self):
        from skiritai.core.execution_manager import (
            register_execution, cancel_execution, unregister_execution,
            is_running, _executions,
        )

        async def _test():
            _ensure_clean()

            async def work():
                await asyncio.sleep(60)

            task = asyncio.create_task(work())
            try:
                register_execution("lifecycle_case", task)
                assert is_running("lifecycle_case") is True
                assert "lifecycle_case" in _executions

                cancelled = await cancel_execution("lifecycle_case")
                assert cancelled is True
                assert is_running("lifecycle_case") is False
                assert "lifecycle_case" not in _executions

                unregister_execution("lifecycle_case")  # should not raise
            finally:
                try:
                    task.cancel()
                except Exception:
                    pass
                _ensure_clean()

        asyncio.run(_test())

    def test_multiple_independent_cases(self):
        from skiritai.core.execution_manager import (
            register_execution, cancel_execution, is_running, _executions,
        )

        async def _test():
            _ensure_clean()

            async def work():
                await asyncio.sleep(60)

            task_a = asyncio.create_task(work())
            task_b = asyncio.create_task(work())
            task_c = asyncio.create_task(work())
            try:
                register_execution("A", task_a)
                register_execution("B", task_b)
                register_execution("C", task_c)

                assert is_running("A") and is_running("B") and is_running("C")
                assert len(_executions) == 3

                await cancel_execution("B")
                assert is_running("A") is True
                assert is_running("B") is False
                assert is_running("C") is True
                assert len(_executions) == 2
                assert "B" not in _executions
            finally:
                for t in [task_a, task_b, task_c]:
                    try:
                        t.cancel()
                    except Exception:
                        pass
                _ensure_clean()

        asyncio.run(_test())


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
