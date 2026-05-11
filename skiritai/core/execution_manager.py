"""Execution manager — tracks running case executions and provides cancellation.

Shared service used by both REST router and WebSocket router.
"""
from __future__ import annotations

import asyncio

from skiritai.logger import logger

# Active execution tasks keyed by case_id
_executions: dict[str, asyncio.Task] = {}
_lock = asyncio.Lock()


async def register_execution(case_id: str, task: asyncio.Task) -> None:
    """Register a running execution task."""
    async with _lock:
        _executions[case_id] = task


async def cancel_execution(case_id: str) -> bool:
    """Cancel a running execution for the given case_id. Returns True if cancelled."""
    async with _lock:
        task = _executions.pop(case_id, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"[ExecMgr] Execution cancelled for case: {case_id}")
        return True
    return False


async def unregister_execution(case_id: str) -> None:
    """Remove an execution from tracking (called when task finishes)."""
    async with _lock:
        _executions.pop(case_id, None)


async def is_running(case_id: str) -> bool:
    """Check if a case is currently running."""
    async with _lock:
        task = _executions.get(case_id)
    return task is not None and not task.done()
