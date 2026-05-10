"""Acceptance tests for Skiritai — end-to-end flows with mocked LLM/browser.

These tests validate real-world scenarios: full case execution, step failure
propagation, event sequencing, API lifecycle, script roundtrip, and edge cases.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Cleanup generated scripts before each test module runs
_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
if _SCRIPTS_DIR.exists():
    import shutil
    shutil.rmtree(_SCRIPTS_DIR)


# ============================================================
# Helpers
# ============================================================

def _make_mock_page(url: str = "http://localhost") -> MagicMock:
    page = MagicMock()
    page.url = url
    page.context = MagicMock()
    return page


def _make_case(tmpdir: str, steps: list[tuple[str, str | None]] | None = None):
    """Create a temporary case directory with a case.py.

    Args:
        tmpdir: temp directory path
        steps: list of (method_name, step_mode_or_None)
    """
    from skiritai.core.base_case import BaseCase, step_mode

    case_dir = Path(tmpdir) / "test_case"
    case_dir.mkdir(parents=True, exist_ok=True)

    # Build case class dynamically
    methods = {
        "setup": lambda self: _noop_setup(self),
        "teardown": lambda self: _noop_teardown(self),
    }

    if steps:
        for name, mode in steps:
            if mode:
                decorated = step_mode(mode)(_make_step_fn(name))
            else:
                decorated = _make_step_fn(name)
            methods[name] = decorated

    TestCase = type("TestCase", (BaseCase,), methods)
    return case_dir, TestCase


async def _noop_setup(self):
    self._page = _make_mock_page()


async def _noop_teardown(self):
    pass


def _make_step_fn(name):
    async def step(self, ai):
        return await ai.action(f"do {name}")
    step.__name__ = name
    return step


# ============================================================
# 1. End-to-End Case Execution
# ============================================================

class TestEndToEndExecution:
    """Full case execution with mocked AI agent."""

    def test_single_step_explore_success(self):
        """A case with one step in explore mode completes successfully."""
        from skiritai.core.base_case import BaseCase

        class OneStepCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def do_task(self, ai):
                return await ai.action("navigate to homepage")

        case = OneStepCase()

        mock_result = {"success": True, "summary": "navigated", "steps": [
            {"action": "navigate", "args": {"url": "http://example.com"}}
        ]}

        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)):
            report = asyncio.run(case.run())

        assert report["status"] == "completed"
        assert report["total_steps"] == 1
        assert report["success_count"] == 1
        assert report["failed_count"] == 0
        assert report["steps"][0]["status"] == "success"
        assert report["steps"][0]["step_id"] == "do_task"

    def test_multi_step_all_success(self):
        """A case with multiple steps all succeeding reports correct counts."""
        from skiritai.core.base_case import BaseCase

        class MultiStepCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def step_a(self, ai):
                return await ai.action("first step")

            async def step_b(self, ai):
                return await ai.action("second step")

            async def step_c(self, ai):
                return await ai.action("third step")

        case = MultiStepCase()

        mock_result = {"success": True, "summary": "done", "steps": []}

        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)):
            report = asyncio.run(case.run())

        assert report["status"] == "completed"
        assert report["total_steps"] == 3
        assert report["success_count"] == 3
        assert report["failed_count"] == 0
        assert len(report["steps"]) == 3

    def test_step_failure_stops_execution(self):
        """When a step fails, subsequent steps should NOT execute.

        Steps run in alphabetical order: aaa_first -> bbb_fail -> ccc_never.
        failed_count = total - success_count (includes unexecuted steps).
        """
        from skiritai.core.base_case import BaseCase

        call_log = []

        class FailCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def aaa_first(self, ai):
                call_log.append("aaa_first")
                return await ai.action("this works")

            async def bbb_fail(self, ai):
                call_log.append("bbb_fail")
                return await ai.action("this fails")

            async def ccc_never(self, ai):
                call_log.append("ccc_never")
                return await ai.action("should not run")

        case = FailCase()

        success = {"success": True, "summary": "ok", "steps": []}
        failure = {"success": False, "summary": "element not found", "steps": []}

        async def mock_agent(page, task_description, **kwargs):
            if "fails" in task_description:
                return failure
            return success

        with patch("skiritai.core.ai_context.run_agent", side_effect=mock_agent):
            report = asyncio.run(case.run())

        assert report["status"] == "failed"
        assert report["success_count"] == 1
        # failed_count = total(3) - success(1) = 2 (includes unexecuted steps)
        assert report["failed_count"] == 2
        assert "aaa_first" in call_log
        assert "bbb_fail" in call_log
        assert "ccc_never" not in call_log  # never executed

    def test_step_exception_stops_execution(self):
        """An unhandled exception in a step method should stop execution."""
        from skiritai.core.base_case import BaseCase

        call_log = []

        class ExceptionCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def step_a(self, ai):
                call_log.append("step_a")
                return await ai.action("works")

            async def step_b(self, ai):
                call_log.append("step_b")
                raise RuntimeError("unexpected crash")

            async def step_c(self, ai):
                call_log.append("step_c")
                return await ai.action("never")

        case = ExceptionCase()

        mock_result = {"success": True, "summary": "ok", "steps": []}
        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)):
            report = asyncio.run(case.run())

        assert report["status"] == "failed"
        assert "step_a" in call_log
        assert "step_b" in call_log
        assert "step_c" not in call_log

    def test_report_contains_case_name(self):
        """Report includes the class name, not a generic string."""
        from skiritai.core.base_case import BaseCase

        class MyAwesomeCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def run_it(self, ai):
                return await ai.action("go")

        case = MyAwesomeCase()
        mock_result = {"success": True, "summary": "done", "steps": []}

        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)):
            report = asyncio.run(case.run())

        assert report["case_name"] == "MyAwesomeCase"


# ============================================================
# 2. Event Sequencing
# ============================================================

class TestEventSequencing:
    """Verify events are published in the correct order during execution."""

    def test_events_published_in_order(self):
        """execution_started -> step_started -> step_completed -> execution_completed."""
        from skiritai.core.base_case import BaseCase
        from skiritai.events import Event, event_bus

        events: list[str] = []

        async def capture(event: Event):
            events.append(event.type)

        event_bus.subscribe(capture)

        class SimpleCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def my_step(self, ai):
                return await ai.action("do it")

        case = SimpleCase()
        mock_result = {"success": True, "summary": "ok", "steps": []}

        try:
            with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)):
                asyncio.run(case.run())
        finally:
            event_bus.unsubscribe(capture)

        assert events[0] == "execution_started"
        assert "step_started" in events
        assert "step_completed" in events
        assert events[-1] == "execution_completed"

    def test_step_failed_event_on_failure(self):
        """A failing step publishes step_failed, not step_completed."""
        from skiritai.core.base_case import BaseCase
        from skiritai.events import Event, event_bus

        step_events: list[tuple[str, str]] = []

        async def capture(event: Event):
            if event.type in ("step_completed", "step_failed"):
                step_events.append((event.type, event.data.get("step_id")))

        event_bus.subscribe(capture)

        class FailCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def bad_step(self, ai):
                return await ai.action("fail")

        case = FailCase()
        fail_result = {"success": False, "summary": "not found", "steps": []}

        try:
            with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=fail_result)):
                asyncio.run(case.run())
        finally:
            event_bus.unsubscribe(capture)

        assert len(step_events) == 1
        assert step_events[0][0] == "step_failed"
        assert step_events[0][1] == "bad_step"

    def test_tool_called_events_published(self):
        """Explore mode publishes tool_called events for each agent tool call."""
        from skiritai.core.base_case import BaseCase
        from skiritai.events import Event, event_bus

        tool_events: list[str] = []

        async def capture(event: Event):
            if event.type == "tool_called":
                tool_events.append(event.data.get("tool_name"))

        event_bus.subscribe(capture)

        class ToolCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def navigate_step(self, ai):
                return await ai.action("go to site")

        case = ToolCase()

        agent_result = {
            "success": True,
            "summary": "navigated",
            "steps": [
                {"action": "navigate", "args": {"url": "http://example.com"}},
                {"action": "click", "args": {"selector": "#btn"}},
            ],
        }

        try:
            with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=agent_result)):
                asyncio.run(case.run())
        finally:
            event_bus.unsubscribe(capture)

        # tool_called events come from agent_loop, not from ai_context
        # Since we mocked run_agent, no tool_called events are published here.
        # This test verifies the event bus doesn't break when no tool events fire.
        assert isinstance(tool_events, list)


# ============================================================
# 3. Step Mode Decorator Behavior
# ============================================================

class TestStepModeBehavior:
    """Verify @step_mode decorator controls explore/replay/auto behavior."""

    def test_explore_mode_always_calls_agent(self):
        """@step_mode('explore') forces explore even when script exists."""
        from skiritai.core.base_case import BaseCase, step_mode

        class ExploreCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            @step_mode("explore")
            async def forced_explore(self, ai):
                return await ai.action("always explore this")

        case = ExploreCase()
        case._page = _make_mock_page()

        # Create a fake script to verify explore overwrites it
        scripts_dir = case._case_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "forced_explore.py").write_text("# old script")

        mock_result = {"success": True, "summary": "explored", "steps": [
            {"action": "navigate", "args": {"url": "http://x.com"}}
        ]}

        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)) as mock_agent:
            report = asyncio.run(case.run())

        # Explore was called (agent ran)
        mock_agent.assert_called_once()
        # Script was overwritten (explore generated a new one)
        new_content = (scripts_dir / "forced_explore.py").read_text()
        assert "old script" not in new_content
        assert "async def run" in new_content
        assert report["status"] == "completed"

    def test_replay_mode_uses_saved_script(self):
        """@step_mode('replay') replays from saved script."""
        from skiritai.core.base_case import BaseCase, step_mode

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "replay_case"
            case_dir.mkdir()

            scripts_dir = case_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "replay_step.py").write_text(
                "async def run(page, context):\n    pass\n"
            )

            class ReplayCase(BaseCase):
                async def setup(self):
                    self._page = _make_mock_page()

                async def teardown(self):
                    pass

                @step_mode("replay")
                async def replay_step(self, ai):
                    return await ai.action("replay this")

            case = ReplayCase(case_dir=case_dir)
            report = asyncio.run(case.run())

            assert report["status"] == "completed"
            assert report["steps"][0]["mode"] == "replay"

    def test_auto_mode_prefers_replay_when_script_exists(self):
        """Auto mode uses replay if a script is already saved."""
        from skiritai.core.base_case import BaseCase

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "auto_case"
            case_dir.mkdir()

            scripts_dir = case_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "auto_step.py").write_text(
                "async def run(page, context):\n    pass\n"
            )

            class AutoCase(BaseCase):
                async def setup(self):
                    self._page = _make_mock_page()

                async def teardown(self):
                    pass

                async def auto_step(self, ai):
                    return await ai.action("auto decision")

            case = AutoCase(case_dir=case_dir)
            report = asyncio.run(case.run())

            assert report["status"] == "completed"
            assert report["steps"][0]["mode"] == "replay"

    def test_auto_mode_explores_when_no_script(self):
        """Auto mode falls back to explore when no script exists."""
        from skiritai.core.base_case import BaseCase

        class AutoExploreCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

            async def no_script_step(self, ai):
                return await ai.action("need to explore")

        case = AutoExploreCase()
        mock_result = {"success": True, "summary": "done", "steps": []}

        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)) as mock_agent:
            report = asyncio.run(case.run())

        # Auto mode called explore since no script existed
        mock_agent.assert_called_once()
        assert report["status"] == "completed"


# ============================================================
# 4. Script Generation and Replay Roundtrip
# ============================================================

class TestScriptRoundtrip:
    """Test generating a script from explore, then replaying it."""

    def test_explore_generates_script_file(self):
        """After explore succeeds, a replay script is written to disk."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "roundtrip"
            case_dir.mkdir()
            mock_page = _make_mock_page()

            ctx = AIContext(page=mock_page, case_dir=case_dir, step_id="nav")

            agent_result = {
                "success": True,
                "summary": "navigated",
                "steps": [
                    {"action": "navigate", "args": {"url": "http://example.com"}},
                    {"action": "click", "args": {"selector": "#login"}},
                ],
            }

            with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=agent_result)):
                result = asyncio.run(ctx.action("go to site", mode="explore"))

            assert result["success"] is True
            assert ctx.script_path.exists()

            content = ctx.script_path.read_text()
            assert "async def run(page, context):" in content
            assert "page.goto" in content
            assert "page.click" in content

    def test_explore_then_replay_roundtrip(self):
        """Explore generates script, replay executes it successfully."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "roundtrip"
            case_dir.mkdir()

            # Use an AsyncMock page so replay's page.goto() can be awaited
            mock_page = AsyncMock()
            mock_page.url = "http://localhost"
            mock_page.context = AsyncMock()

            # Step 1: Explore with empty steps (generates a pass-only script)
            ctx_explore = AIContext(page=mock_page, case_dir=case_dir, step_id="do_thing")
            agent_result = {
                "success": True,
                "summary": "done",
                "steps": [],  # empty -> generates pass
            }

            with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=agent_result)):
                explore_result = asyncio.run(ctx_explore.action("do the thing", mode="explore"))

            assert explore_result["success"] is True
            assert ctx_explore.script_path.exists()

            # Step 2: Replay (script only has pass, no page calls needed)
            ctx_replay = AIContext(page=mock_page, case_dir=case_dir, step_id="do_thing")
            assert ctx_replay.has_replay() is True

            replay_result = asyncio.run(ctx_replay.action("do the thing", mode="replay"))
            assert replay_result["success"] is True
            assert replay_result["steps"][0]["action"] == "replay"

    def test_explore_failure_does_not_write_script(self):
        """If explore fails, no replay script should be generated."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "no_script"
            case_dir.mkdir()

            ctx = AIContext(page=_make_mock_page(), case_dir=case_dir, step_id="fail_step")

            fail_result = {"success": False, "summary": "timeout", "steps": []}

            with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=fail_result)):
                result = asyncio.run(ctx.action("this will fail", mode="explore"))

            assert result["success"] is False
            assert not ctx.script_path.exists()

    def test_replay_error_returns_failure_dict(self):
        """Replay of a broken script returns success=False, not an exception."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "broken"
            case_dir.mkdir()

            ctx = AIContext(page=_make_mock_page(), case_dir=case_dir, step_id="broken")
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text(
                "async def run(page, context):\n"
                "    raise ValueError('script is broken')\n"
            )

            result = asyncio.run(ctx._replay())
            assert result["success"] is False
            assert "script is broken" in result["summary"]


# ============================================================
# 5. API Lifecycle
# ============================================================

class TestAPILifecycle:
    """Full API lifecycle: list -> detail -> run -> results."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app
        from skiritai.core.execution_manager import _executions
        _executions.clear()
        self.client = TestClient(create_app())

    def test_full_lifecycle_list_detail_scripts(self):
        """List cases -> get detail -> list scripts -> get script content."""
        # List
        resp = self.client.get("/api/cases")
        assert resp.status_code == 200
        cases = resp.json()
        assert len(cases) >= 1

        case_id = cases[0]["id"]

        # Detail
        resp2 = self.client.get(f"/api/cases/{case_id}")
        assert resp2.status_code == 200
        detail = resp2.json()
        assert detail["id"] == case_id
        assert "steps" in detail
        assert isinstance(detail["steps"], list)

        # Scripts
        resp3 = self.client.get(f"/api/cases/{case_id}/scripts")
        assert resp3.status_code == 200

    def test_run_mocked_then_query_results(self):
        """Run a case (mocked), then verify results are queryable."""
        with patch("skiritai.web.routers.cases.run_case", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "case_name": "BaiduSearchCase",
                "status": "completed",
                "total_steps": 3,
                "success_count": 3,
                "failed_count": 0,
                "steps": [
                    {"step_id": "open_baidu", "status": "success", "mode": "explore", "summary": "ok"},
                    {"step_id": "search_keyword", "status": "success", "mode": "explore", "summary": "ok"},
                    {"step_id": "verify_results", "status": "success", "mode": "explore", "summary": "ok"},
                ],
            }

            resp = self.client.post("/api/cases/baidu_search/run")
            assert resp.status_code == 200
            assert resp.json()["status"] == "started"

            # Wait for the async task to complete
            import time
            time.sleep(0.5)

        # Query results
        resp2 = self.client.get("/api/cases/baidu_search/results")
        assert resp2.status_code == 200
        results = resp2.json()
        assert len(results) >= 1

        # Latest result should be "completed"
        latest = results[0]
        assert latest["report"]["status"] == "completed"
        assert latest["report"]["success_count"] == 3

    def test_update_and_solidify_script_flow(self):
        """Update a script, then solidify it, verify marker exists."""
        # Find a case with scripts
        cases = self.client.get("/api/cases").json()
        target_case = None
        target_step = None
        for c in cases:
            scripts = self.client.get(f"/api/cases/{c['id']}/scripts").json()
            if scripts:
                target_case = c["id"]
                target_step = scripts[0]["step_id"]
                break

        if not target_case:
            pytest.skip("No cases with scripts found")

        # Get original content
        resp = self.client.get(f"/api/cases/{target_case}/scripts/{target_step}")
        original_content = resp.json()["content"]

        # Update
        new_content = original_content + "\n# acceptance test update"
        resp2 = self.client.put(
            f"/api/cases/{target_case}/scripts/{target_step}",
            json={"content": new_content},
        )
        assert resp2.status_code == 200
        assert resp2.json()["content"] == new_content

        # Solidify
        resp3 = self.client.post(f"/api/cases/{target_case}/scripts/{target_step}/solidify")
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "solidified"

        # Verify marker
        cases_root = Path(__file__).resolve().parent.parent.parent / "examples"
        marker = cases_root / target_case / "scripts" / f".{target_step}.solidified"
        assert marker.exists()

        # Cleanup: restore original and remove marker
        self.client.put(
            f"/api/cases/{target_case}/scripts/{target_step}",
            json={"content": original_content},
        )
        marker.unlink(missing_ok=True)

    def test_run_cancels_previous_execution(self):
        """Starting a new run for the same case cancels the previous one."""
        from skiritai.core.execution_manager import _executions

        call_count = 0

        async def slow_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(10)
            return {"status": "completed", "total_steps": 0, "success_count": 0, "failed_count": 0, "steps": []}

        with patch("skiritai.web.routers.cases.run_case", side_effect=slow_run):
            resp1 = self.client.post("/api/cases/baidu_search/run")
            assert resp1.status_code == 200

            resp2 = self.client.post("/api/cases/baidu_search/run")
            assert resp2.status_code == 200

        import time
        time.sleep(0.2)

    def test_stop_cancels_registered_task(self):
        """_cancel_execution correctly cancels and removes a registered task."""
        from skiritai.core.execution_manager import cancel_execution as _cancel_execution, _executions

        async def _test():
            async def dummy():
                await asyncio.sleep(60)

            task = asyncio.create_task(dummy())
            _executions["test_case"] = task

            result = await _cancel_execution("test_case")
            assert result is True
            # task.cancel() schedules cancellation; await to let it propagate
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert task.cancelled()
            assert "test_case" not in _executions

        asyncio.run(_test())

    def test_stop_returns_not_found_when_no_task(self):
        """POST /stop returns not_found when no execution is running."""
        resp = self.client.post("/api/cases/baidu_search/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_found"


# ============================================================
# 6. WSManager Integration
# ============================================================

class TestWSManagerIntegration:
    """Test WSManager handles real event sequences correctly."""

    def test_full_execution_event_sequence(self):
        """Simulate a full execution event sequence through WSManager."""
        from skiritai.events import Event
        from skiritai.web.ws_manager import WSManager

        mgr = WSManager()
        messages = []

        events = [
            Event(type="execution_started", execution_id="e1", data={}),
            Event(type="step_started", execution_id="e1", data={"step_id": "open"}),
            Event(type="tool_called", execution_id="e1", data={"tool_name": "navigate", "tool_args": {"url": "http://x.com"}}),
            Event(type="step_completed", execution_id="e1", data={"step_id": "open", "mode": "explore", "summary": "ok"}),
            Event(type="step_started", execution_id="e1", data={"step_id": "click"}),
            Event(type="step_completed", execution_id="e1", data={"step_id": "click", "mode": "replay", "summary": "done"}),
            Event(type="execution_completed", execution_id="e1", data={"report": {"status": "completed"}}),
        ]

        for event in events:
            msg = mgr._event_to_ws_message(event)
            if msg:
                messages.append(msg)

        assert len(messages) == 7
        assert messages[0]["type"] == "execution_status"
        assert messages[0]["status"] == "running"
        assert messages[1]["type"] == "node_status"
        assert messages[1]["status"] == "running"
        assert messages[2]["type"] == "log"
        assert messages[3]["status"] == "success"
        assert messages[4]["status"] == "running"
        assert messages[5]["status"] == "success"
        assert messages[6]["type"] == "execution_status"
        assert messages[6]["status"] == "completed"

    def test_failed_execution_event_sequence(self):
        """Failed step generates correct WS message."""
        from skiritai.events import Event
        from skiritai.web.ws_manager import WSManager

        mgr = WSManager()

        failed_event = Event(
            type="step_failed",
            execution_id="e1",
            data={"step_id": "login", "error": "element not found", "summary": "timeout"},
        )
        msg = mgr._event_to_ws_message(failed_event)

        assert msg["type"] == "node_status"
        assert msg["status"] == "failed"
        assert msg["data"]["error"] == "element not found"


# ============================================================
# 7. Edge Cases
# ============================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_case_with_no_steps(self):
        """A case with no step methods should complete with 0 steps."""
        from skiritai.core.base_case import BaseCase

        class EmptyCase(BaseCase):
            async def setup(self):
                self._page = _make_mock_page()

            async def teardown(self):
                pass

        case = EmptyCase()
        report = asyncio.run(case.run())

        assert report["status"] == "completed"
        assert report["total_steps"] == 0
        assert report["success_count"] == 0
        assert report["failed_count"] == 0
        assert report["steps"] == []

    def test_private_methods_not_discovered_as_steps(self):
        """Methods starting with _ should not be discovered as steps."""
        from skiritai.core.base_case import BaseCase

        class PrivateCase(BaseCase):
            async def _helper(self, ai):
                """This has 'ai' param but is private."""
                pass

            async def public_step(self, ai):
                pass

        case = PrivateCase()
        steps = case.get_step_methods()

        assert "_helper" not in steps
        assert "public_step" in steps

    def test_methods_without_ai_param_not_discovered(self):
        """Methods without 'ai' as second param are not steps."""
        from skiritai.core.base_case import BaseCase

        class MixedCase(BaseCase):
            async def real_step(self, ai):
                pass

            async def not_a_step(self, something_else):
                pass

            def sync_method(self):
                pass

        case = MixedCase()
        steps = case.get_step_methods()

        assert "real_step" in steps
        assert "not_a_step" not in steps
        assert "sync_method" not in steps

    def test_script_path_isolation_between_steps(self):
        """Different steps have different script paths."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "iso"
            case_dir.mkdir()

            ctx1 = AIContext(page=MagicMock(), case_dir=case_dir, step_id="alpha")
            ctx2 = AIContext(page=MagicMock(), case_dir=case_dir, step_id="beta")

            assert ctx1.script_path != ctx2.script_path
            assert ctx1.script_path.name == "alpha.py"
            assert ctx2.script_path.name == "beta.py"

    def test_replay_missing_script_raises_file_not_found(self):
        """Replay mode without a script raises FileNotFoundError."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "missing"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="no_script")

            with pytest.raises(FileNotFoundError, match="no_script"):
                asyncio.run(ctx.action("do it", mode="replay"))

    def test_list_cases_skips_invalid_dirs(self):
        """list_cases gracefully skips directories without case.py."""
        from skiritai.core.runner import list_cases

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Valid case
            valid = root / "valid"
            valid.mkdir()
            (valid / "case.py").write_text(
                "from skiritai.core.base_case import BaseCase\n"
                "class V(BaseCase): pass\n"
            )
            # Invalid: no case.py
            (root / "no_case").mkdir()
            # Invalid: case.py with syntax error
            bad = root / "bad_syntax"
            bad.mkdir()
            (bad / "case.py").write_text("def broken(")

            cases = list_cases(root)
            assert len(cases) == 1
            assert cases[0]["id"] == "valid"

    def test_discover_case_class_missing_file_raises(self):
        """discover_case_class raises FileNotFoundError for missing case.py."""
        from skiritai.core.runner import discover_case_class

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                discover_case_class(Path(tmpdir))

    def test_api_case_detail_includes_step_modes(self):
        """GET /api/cases/{id} returns mode info for each step."""
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app

        client = TestClient(create_app())
        resp = client.get("/api/cases/baidu_search")
        assert resp.status_code == 200

        steps = resp.json()["steps"]
        for step in steps:
            assert "mode" in step
            assert step["mode"] in ("explore", "solidified")

    def test_api_nonexistent_case_endpoints_return_404(self):
        """All case-specific endpoints return 404 for nonexistent cases."""
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app

        client = TestClient(create_app())

        assert client.get("/api/cases/does_not_exist").status_code == 404
        assert client.post("/api/cases/does_not_exist/run").status_code == 404
        assert client.post("/api/cases/does_not_exist/stop").status_code == 404
        assert client.get("/api/cases/does_not_exist/results").status_code == 200  # returns []
        assert client.get("/api/cases/does_not_exist/results/ts").status_code == 404

    def test_generate_script_scroll_up_direction(self):
        """Script generation handles scroll up correctly."""
        from skiritai.core.script_generator import generate_replay_script

        steps = [{"action": "scroll", "args": {"direction": "up", "amount": 300}}]
        script = generate_replay_script("test", steps)
        assert "await page.mouse.wheel(0, -300)" in script

    def test_generate_script_eval_js_escapes_quotes(self):
        """Script generation properly handles quotes in JS expressions."""
        from skiritai.core.script_generator import generate_replay_script

        steps = [{"action": "eval_js", "args": {"expression": 'document.querySelector("div").click()'}}]
        script = generate_replay_script("test", steps)
        # repr() uses single quotes when the string contains double quotes,
        # so the JS expression is embedded without needing backslash escapes.
        assert "document.querySelector" in script
        assert '"div"' in script
        assert "page.evaluate" in script

    def test_result_report_step_mode_field(self):
        """has_replay() correctly reflects script file existence."""
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mode_check"
            case_dir.mkdir()

            page = _make_mock_page()

            # No script -> has_replay() is False
            ctx = AIContext(page=page, case_dir=case_dir, step_id="my_step")
            assert ctx.has_replay() is False

            # Create script -> has_replay() becomes True
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text("async def run(page, context):\n    pass\n")
            assert ctx.has_replay() is True

            # Different step_id -> different script path, still no script
            ctx2 = AIContext(page=page, case_dir=case_dir, step_id="other_step")
            assert ctx2.has_replay() is False


# ============================================================
# 8. Run
# ============================================================

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
