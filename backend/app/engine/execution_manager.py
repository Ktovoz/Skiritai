"""Execution manager — tracks running case executions and provides cancellation.

Shared service used by both REST router and WebSocket router.
"""
from __future__ import annotations

import asyncio

from app.logger import logger

# Active execution tasks keyed by case_id
_executions: dict[str, asyncio.Task] = {}


def register_execution(case_id: str, task: asyncio.Task) -> None:
    """Register a running execution task."""
    _executions[case_id] = task


async def cancel_execution(case_id: str) -> bool:
    """Cancel a running execution for the given case_id. Returns True if cancelled."""
    task = _executions.pop(case_id, None)
    if task and not task.done():
        task.cancel()
        logger.info(f"[ExecMgr] Execution cancelled for case: {case_id}")
        return True
    return False


def unregister_execution(case_id: str) -> None:
    """Remove an execution from tracking (called when task finishes)."""
    _executions.pop(case_id, None)


def is_running(case_id: str) -> bool:
    """Check if a case is currently running."""
    task = _executions.get(case_id)
    return task is not None and not task.done()
