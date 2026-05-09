"""Case execution context — global state & state machine for a test case.

A single CaseContext instance is created per case execution and shared across
all steps.  It holds:

- **State machine**: tracks execution phase (idle → setup → running → teardown → done/failed)
- **Browser session**: CDP port, PID, mode (standard / persistent)
- **Global store**: arbitrary key-value data that persists across steps
- **Perception mode**: whether to use Playwright evaluate or browser-use DomService

Typical lifecycle::

    ctx = CaseContext(case_dir=Path("cases/my_case"))
    await ctx.transition("setup")
    ctx.cdp_port = 9222
    ctx.store.set("login_token", "abc123")
    ...
    await ctx.transition("done")
"""

from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any

from app.logger import logger

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class CasePhase(str, Enum):
    """Execution phases for a test case."""
    IDLE = "idle"
    SETUP = "setup"
    RUNNING = "running"
    TEARDOWN = "teardown"
    DONE = "done"
    FAILED = "failed"
    PAUSED = "paused"


# Valid transitions: current_phase → set of allowed next phases
_TRANSITIONS: dict[CasePhase, set[CasePhase]] = {
    CasePhase.IDLE:     {CasePhase.SETUP, CasePhase.PAUSED},
    CasePhase.SETUP:    {CasePhase.RUNNING, CasePhase.FAILED, CasePhase.PAUSED},
    CasePhase.RUNNING:  {CasePhase.TEARDOWN, CasePhase.FAILED, CasePhase.PAUSED},
    CasePhase.TEARDOWN: {CasePhase.DONE, CasePhase.FAILED},
    CasePhase.PAUSED:   {CasePhase.RUNNING, CasePhase.TEARDOWN, CasePhase.FAILED},
    CasePhase.DONE:     set(),
    CasePhase.FAILED:   set(),
}


class StateError(Exception):
    """Raised when an invalid state transition is attempted."""


# ---------------------------------------------------------------------------
# Global store
# ---------------------------------------------------------------------------

class GlobalStore:
    """Simple key-value store that persists for the lifetime of a case.

    Thread-safe for single-async-loop usage (which is our case).
    Can be snapshotted to / restored from JSON for crash recovery.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def has(self, key: str) -> bool:
        return key in self._data

    def remove(self, key: str) -> Any | None:
        return self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def load_dict(self, data: dict[str, Any]) -> None:
        self._data.update(data)

    def __repr__(self) -> str:
        return f"GlobalStore({self._data})"


# ---------------------------------------------------------------------------
# Browser session info
# ---------------------------------------------------------------------------

class BrowserSessionInfo:
    """Tracks browser connection details for the current case."""

    def __init__(self) -> None:
        self.mode: str = ""          # "standard" or "persistent"
        self.cdp_port: int | None = None
        self.pid: int | None = None
        self.started_at: float | None = None
        self.ws_endpoint: str | None = None

    @property
    def is_persistent(self) -> bool:
        return self.mode == "persistent"

    @property
    def is_active(self) -> bool:
        return self.cdp_port is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "cdp_port": self.cdp_port,
            "pid": self.pid,
            "started_at": self.started_at,
            "ws_endpoint": self.ws_endpoint,
        }


# ---------------------------------------------------------------------------
# Main context
# ---------------------------------------------------------------------------

class CaseContext:
    """Global context for a single test case execution.

    Created once per case run, shared by all steps.
    """

    def __init__(
        self,
        case_dir: Path,
        execution_id: str = "default",
        perception_mode: str = "playwright",  # "playwright" or "browser_use"
    ) -> None:
        self.case_dir = case_dir
        self.execution_id = execution_id
        self.perception_mode = perception_mode

        # State machine
        self._phase = CasePhase.IDLE
        self._phase_history: list[tuple[CasePhase, float]] = [(CasePhase.IDLE, time.time())]

        # Sub-systems
        self.store = GlobalStore()
        self.browser = BrowserSessionInfo()

        # Step tracking
        self.current_step: str | None = None
        self.completed_steps: list[str] = []
        self.failed_step: str | None = None

        # Timing
        self.started_at: float | None = None
        self.finished_at: float | None = None

    # ---- State machine ----

    @property
    def phase(self) -> CasePhase:
        return self._phase

    def can_transition(self, target: CasePhase | str) -> bool:
        target = CasePhase(target)
        return target in _TRANSITIONS.get(self._phase, set())

    async def transition(self, target: CasePhase | str) -> None:
        """Transition to a new phase. Validates the transition is allowed."""
        target = CasePhase(target)
        allowed = _TRANSITIONS.get(self._phase, set())
        if target not in allowed:
            raise StateError(
                f"Cannot transition from {self._phase.value} → {target.value}. "
                f"Allowed: {[p.value for p in allowed]}"
            )
        old = self._phase
        self._phase = target
        self._phase_history.append((target, time.time()))
        logger.info(f"[Context] Phase: {old.value} → {target.value}")

        # Auto-set timing
        if target == CasePhase.SETUP and self.started_at is None:
            self.started_at = time.time()
        if target in (CasePhase.DONE, CasePhase.FAILED):
            self.finished_at = time.time()

    def assert_phase(self, expected: CasePhase | str) -> None:
        """Raise if not in the expected phase."""
        expected = CasePhase(expected)
        if self._phase != expected:
            raise StateError(
                f"Expected phase {expected.value}, but current is {self._phase.value}"
            )

    @property
    def phase_history(self) -> list[tuple[str, float]]:
        return [(p.value, t) for p, t in self._phase_history]

    @property
    def elapsed_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at or time.time()
        return round(end - self.started_at, 2)

    # ---- Snapshot / restore ----

    def snapshot(self) -> dict[str, Any]:
        """Serialize current state for persistence or debugging."""
        return {
            "execution_id": self.execution_id,
            "phase": self._phase.value,
            "perception_mode": self.perception_mode,
            "browser": self.browser.to_dict(),
            "store": self.store.to_dict(),
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "failed_step": self.failed_step,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": self.elapsed_seconds,
            "phase_history": self.phase_history,
        }

    def save_snapshot(self) -> Path:
        """Save snapshot to case_dir."""
        path = self.case_dir / ".case_context"
        path.write_text(json.dumps(self.snapshot(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"[Context] Snapshot saved to {path}")
        return path

    @classmethod
    def load_snapshot(cls, case_dir: Path) -> CaseContext | None:
        """Load context from a saved snapshot. Returns None if not found."""
        path = case_dir / ".case_context"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ctx = cls(
                case_dir=case_dir,
                execution_id=data.get("execution_id", "default"),
                perception_mode=data.get("perception_mode", "playwright"),
            )
            ctx._phase = CasePhase(data.get("phase", "idle"))
            ctx.store.load_dict(data.get("store", {}))
            ctx.browser.cdp_port = data.get("browser", {}).get("cdp_port")
            ctx.browser.pid = data.get("browser", {}).get("pid")
            ctx.browser.mode = data.get("browser", {}).get("mode", "")
            ctx.browser.started_at = data.get("browser", {}).get("started_at")
            ctx.current_step = data.get("current_step")
            ctx.completed_steps = data.get("completed_steps", [])
            ctx.failed_step = data.get("failed_step")
            ctx.started_at = data.get("started_at")
            ctx.finished_at = data.get("finished_at")
            return ctx
        except Exception as e:
            logger.warning(f"[Context] Failed to load snapshot: {e}")
            return None

    def __repr__(self) -> str:
        return (
            f"CaseContext(phase={self._phase.value}, "
            f"steps={len(self.completed_steps)}/{len(self.completed_steps) + (1 if self.current_step else 0)}, "
            f"browser={'port=' + str(self.browser.cdp_port) if self.browser.cdp_port else 'none'})"
        )
