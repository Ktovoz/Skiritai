"""Unit tests for CaseContext — state machine, GlobalStore, BrowserSessionInfo."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest


# ============================================================
# 1. GlobalStore Tests
# ============================================================

class TestGlobalStore:
    """Test GlobalStore key-value operations and snapshot."""

    def test_get_set_and_has(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        assert store.has("key") is False
        assert store.get("key") is None
        assert store.get("key", "fallback") == "fallback"

        store.set("key", "value")
        assert store.has("key") is True
        assert store.get("key") == "value"

    def test_set_overwrites(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("a", 1)
        store.set("a", 2)
        assert store.get("a") == 2

    def test_remove_existing_and_missing(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("a", 1)
        assert store.remove("a") == 1
        assert store.has("a") is False
        assert store.remove("nonexistent") is None

    def test_clear_removes_all(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("a", 1)
        store.set("b", 2)
        store.clear()
        assert store.has("a") is False
        assert store.has("b") is False
        assert store.to_dict() == {}

    def test_to_dict_returns_copy(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("a", 1)
        d = store.to_dict()
        d["a"] = 999
        assert store.get("a") == 1  # original unaffected

    def test_load_dict_updates_data(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("existing", True)
        store.load_dict({"a": 1, "b": 2, "existing": False})
        assert store.get("a") == 1
        assert store.get("b") == 2
        assert store.get("existing") is False  # overwritten

    def test_repr_includes_data(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("k", "v")
        r = repr(store)
        assert "GlobalStore" in r
        assert "k" in r

    def test_handles_complex_values(self):
        from app.engine.case_context import GlobalStore

        store = GlobalStore()
        store.set("list", [1, 2, 3])
        store.set("dict", {"nested": True})
        store.set("none", None)
        assert store.get("list") == [1, 2, 3]
        assert store.get("dict") == {"nested": True}
        assert store.get("none") is None


# ============================================================
# 2. BrowserSessionInfo Tests
# ============================================================

class TestBrowserSessionInfo:
    """Test BrowserSessionInfo properties and serialization."""

    def test_defaults_are_empty(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        assert info.mode == ""
        assert info.cdp_port is None
        assert info.pid is None
        assert info.started_at is None
        assert info.ws_endpoint is None

    def test_is_persistent_false_for_standard(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        info.mode = "standard"
        assert info.is_persistent is False

    def test_is_persistent_true_for_persistent(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        info.mode = "persistent"
        assert info.is_persistent is True

    def test_is_active_false_when_no_port(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        assert info.is_active is False

    def test_is_active_true_when_port_set(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        info.cdp_port = 9222
        assert info.is_active is True

    def test_to_dict_includes_all_fields(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        info.mode = "persistent"
        info.cdp_port = 9222
        info.pid = 12345
        info.started_at = 1000.0
        info.ws_endpoint = "ws://localhost:9222/devtools"

        d = info.to_dict()
        assert d["mode"] == "persistent"
        assert d["cdp_port"] == 9222
        assert d["pid"] == 12345
        assert d["started_at"] == 1000.0
        assert d["ws_endpoint"] == "ws://localhost:9222/devtools"

    def test_to_dict_with_none_values(self):
        from app.engine.case_context import BrowserSessionInfo

        info = BrowserSessionInfo()
        d = info.to_dict()
        assert d["mode"] == ""
        assert d["cdp_port"] is None
        assert d["pid"] is None


# ============================================================
# 3. CaseContext State Machine Tests
# ============================================================

class TestCaseContextStateMachine:
    """Test CaseContext phase transitions and validation."""

    def test_initial_state_is_idle(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.phase.value == "idle"

    def test_can_transition_to_allowed_phase(self):
        from app.engine.case_context import CaseContext, CasePhase

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.can_transition(CasePhase.SETUP) is True
        assert ctx.can_transition("setup") is True
        assert ctx.can_transition(CasePhase.PAUSED) is True

    def test_cannot_transition_to_disallowed_phase(self):
        from app.engine.case_context import CaseContext, CasePhase

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.can_transition(CasePhase.RUNNING) is False
        assert ctx.can_transition(CasePhase.TEARDOWN) is False
        assert ctx.can_transition(CasePhase.DONE) is False
        assert ctx.can_transition(CasePhase.FAILED) is False

    def test_transition_changes_phase(self):
        from app.engine.case_context import CaseContext, CasePhase

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition(CasePhase.SETUP))
        assert ctx.phase == CasePhase.SETUP

    def test_transition_records_history(self):
        from app.engine.case_context import CaseContext, CasePhase

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition(CasePhase.SETUP))
        asyncio.run(ctx.transition(CasePhase.RUNNING))

        history = ctx.phase_history
        assert len(history) == 3  # idle (initial) + setup + running
        assert history[0][0] == "idle"
        assert history[1][0] == "setup"
        assert history[2][0] == "running"

    def test_invalid_transition_raises_state_error(self):
        from app.engine.case_context import CaseContext, StateError

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        with pytest.raises(StateError, match="Cannot transition"):
            asyncio.run(ctx.transition("running"))

    def test_final_states_cannot_transition(self):
        from app.engine.case_context import CaseContext, StateError, CasePhase

        # DONE is terminal
        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("running"))
        asyncio.run(ctx.transition("teardown"))
        asyncio.run(ctx.transition("done"))
        assert ctx.can_transition("idle") is False
        with pytest.raises(StateError):
            asyncio.run(ctx.transition("running"))

        # FAILED is terminal
        ctx2 = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx2.transition("setup"))
        asyncio.run(ctx2.transition("failed"))
        assert ctx2.can_transition("teardown") is False

    def test_setup_transition_sets_started_at(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.started_at is None
        asyncio.run(ctx.transition("setup"))
        assert ctx.started_at is not None

    def test_done_transition_sets_finished_at(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("running"))
        asyncio.run(ctx.transition("teardown"))
        asyncio.run(ctx.transition("done"))
        assert ctx.finished_at is not None

    def test_failed_transition_sets_finished_at(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("failed"))
        assert ctx.finished_at is not None

    def test_paused_state_allows_resume(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("running"))
        asyncio.run(ctx.transition("paused"))
        assert ctx.phase.value == "paused"
        asyncio.run(ctx.transition("running"))  # resume
        assert ctx.phase.value == "running"

    def test_paused_can_go_to_teardown_or_failed(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("paused"))
        asyncio.run(ctx.transition("teardown"))
        assert ctx.phase.value == "teardown"


# ============================================================
# 4. CaseContext Lifecycle Tests
# ============================================================

class TestCaseContextLifecycle:
    """Test full CaseContext lifecycle: idle → setup → running → teardown → done."""

    def test_full_happy_path(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"), execution_id="exec_123")
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("running"))
        asyncio.run(ctx.transition("teardown"))
        asyncio.run(ctx.transition("done"))

        assert ctx.phase.value == "done"
        assert ctx.execution_id == "exec_123"
        assert ctx.started_at is not None
        assert ctx.finished_at is not None
        assert ctx.elapsed_seconds is not None
        assert ctx.elapsed_seconds >= 0

    def test_setup_to_failed_directly(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        asyncio.run(ctx.transition("failed"))
        assert ctx.phase.value == "failed"
        assert ctx.started_at is not None
        assert ctx.finished_at is not None

    def test_elapsed_seconds_returns_none_before_start(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.elapsed_seconds is None

    def test_elapsed_seconds_grows_during_execution(self):
        from app.engine.case_context import CaseContext
        import time

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        time.sleep(0.01)
        elapsed = ctx.elapsed_seconds
        assert elapsed is not None
        assert elapsed > 0

    def test_current_step_tracking(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.current_step is None
        ctx.current_step = "open_page"
        assert ctx.current_step == "open_page"
        ctx.current_step = None
        assert ctx.current_step is None

    def test_completed_steps_tracking(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.completed_steps == []
        ctx.completed_steps.append("step1")
        ctx.completed_steps.append("step2")
        assert ctx.completed_steps == ["step1", "step2"]

    def test_failed_step_tracking(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.failed_step is None
        ctx.failed_step = "step2"
        assert ctx.failed_step == "step2"

    def test_repr_includes_phase_and_browser(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        r = repr(ctx)
        assert "idle" in r
        assert "none" in r  # browser port is none

        ctx.browser.cdp_port = 9222
        r2 = repr(ctx)
        assert "9222" in r2


# ============================================================
# 5. CaseContext Snapshot / Restore Tests
# ============================================================

class TestCaseContextSnapshot:
    """Test CaseContext.snapshot() / save_snapshot() / load_snapshot()."""

    def test_snapshot_includes_all_keys(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"), execution_id="e1")
        ctx.store.set("token", "abc")
        ctx.browser.cdp_port = 9222
        ctx.current_step = "step1"
        ctx.completed_steps = ["prev"]
        ctx.failed_step = None

        snap = ctx.snapshot()
        assert snap["execution_id"] == "e1"
        assert snap["phase"] == "idle"
        assert snap["perception_mode"] == "playwright"
        assert snap["browser"]["cdp_port"] == 9222
        assert snap["store"]["token"] == "abc"
        assert snap["current_step"] == "step1"
        assert snap["completed_steps"] == ["prev"]
        assert snap["failed_step"] is None
        assert snap["started_at"] is None
        assert snap["finished_at"] is None
        assert "phase_history" in snap

    def test_save_and_load_snapshot_roundtrip(self):
        from app.engine.case_context import CaseContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()

            # Create and modify context
            ctx = CaseContext(case_dir=case_dir, execution_id="exec_1")
            asyncio.run(ctx.transition("setup"))
            asyncio.run(ctx.transition("running"))
            ctx.store.set("key1", "value1")
            ctx.store.set("key2", 42)
            ctx.browser.cdp_port = 9222
            ctx.browser.pid = 9999
            ctx.browser.mode = "persistent"
            ctx.browser.started_at = 1000.0
            ctx.current_step = "search"
            ctx.completed_steps = ["open"]
            ctx.failed_step = None

            # Save
            path = ctx.save_snapshot()
            assert path.exists()
            assert path.name == ".case_context"

            # Load
            loaded = CaseContext.load_snapshot(case_dir)
            assert loaded is not None
            assert loaded.execution_id == "exec_1"
            assert loaded.phase.value == "running"
            assert loaded.store.get("key1") == "value1"
            assert loaded.store.get("key2") == 42
            assert loaded.browser.cdp_port == 9222
            assert loaded.browser.pid == 9999
            assert loaded.browser.mode == "persistent"
            assert loaded.browser.started_at == 1000.0
            assert loaded.current_step == "search"
            assert loaded.completed_steps == ["open"]
            assert loaded.failed_step is None
            assert loaded.started_at is not None
            assert loaded.finished_at is None

    def test_load_snapshot_returns_none_when_missing(self):
        from app.engine.case_context import CaseContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "empty_case"
            case_dir.mkdir()
            result = CaseContext.load_snapshot(case_dir)
            assert result is None

    def test_load_snapshot_handles_corrupt_file(self):
        from app.engine.case_context import CaseContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "corrupt"
            case_dir.mkdir()
            (case_dir / ".case_context").write_text("not valid json {{{")

            result = CaseContext.load_snapshot(case_dir)
            assert result is None  # gracefully returns None

    def test_load_snapshot_defaults_on_missing_keys(self):
        from app.engine.case_context import CaseContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "minimal"
            case_dir.mkdir()
            # Minimal valid snapshot with missing keys
            (case_dir / ".case_context").write_text(
                json.dumps({"execution_id": "min"})
            )

            loaded = CaseContext.load_snapshot(case_dir)
            assert loaded is not None
            assert loaded.execution_id == "min"
            assert loaded.phase.value == "idle"
            assert loaded.perception_mode == "playwright"
            assert loaded.store.to_dict() == {}
            assert loaded.completed_steps == []


# ============================================================
# 6. CaseContext assert_phase Tests
# ============================================================

class TestCaseContextAssertPhase:
    """Test CaseContext.assert_phase() validation."""

    def test_assert_phase_passes_when_correct(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        ctx.assert_phase("setup")  # should not raise

    def test_assert_phase_raises_when_wrong(self):
        from app.engine.case_context import CaseContext, StateError

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        asyncio.run(ctx.transition("setup"))
        with pytest.raises(StateError, match="Expected phase running"):
            ctx.assert_phase("running")


# ============================================================
# 7. CaseContext Constructor and Defaults
# ============================================================

class TestCaseContextConstructor:
    """Test CaseContext constructor and default values."""

    def test_default_execution_id(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.execution_id == "default"

    def test_custom_execution_id(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"), execution_id="custom_123")
        assert ctx.execution_id == "custom_123"

    def test_default_perception_mode(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.perception_mode == "playwright"

    def test_custom_perception_mode(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"), perception_mode="browser_use")
        assert ctx.perception_mode == "browser_use"

    def test_store_is_initialized_empty(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.store.to_dict() == {}

    def test_browser_is_initialized_empty(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.browser.cdp_port is None
        assert ctx.browser.mode == ""

    def test_case_dir_is_stored(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert ctx.case_dir == Path("/tmp/test")

    def test_phase_history_starts_with_idle(self):
        from app.engine.case_context import CaseContext

        ctx = CaseContext(case_dir=Path("/tmp/test"))
        assert len(ctx.phase_history) == 1
        assert ctx.phase_history[0][0] == "idle"


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
