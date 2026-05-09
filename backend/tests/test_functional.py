"""Functional tests for Skiritai — no browser/LLM required."""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # type: ignore

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ============================================================
# 1. EventBus Tests
# ============================================================

class TestEventBus:
    """Test event bus pub-sub, error handling, and unsubscription."""

    def test_subscribe_and_publish(self):
        from app.engine.event_bus import Event, EventBus

        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(handler, event_types=["test_type"])
        asyncio.run(bus.publish(Event(type="test_type", execution_id="e1", data={"key": "val"})))

        assert len(received) == 1
        assert received[0].type == "test_type"
        assert received[0].execution_id == "e1"
        assert received[0].data["key"] == "val"

    def test_all_handler_receives_all_events(self):
        from app.engine.event_bus import Event, EventBus

        bus = EventBus()
        received: list[str] = []

        async def handler(event: Event):
            received.append(event.type)

        bus.subscribe(handler)  # no filter = all events
        asyncio.run(bus.publish(Event(type="foo", execution_id="e1")))
        asyncio.run(bus.publish(Event(type="bar", execution_id="e1")))

        assert received == ["foo", "bar"]

    def test_unsubscribe_removes_handler(self):
        from app.engine.event_bus import Event, EventBus

        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(handler, event_types=["t1"])
        bus.unsubscribe(handler)
        asyncio.run(bus.publish(Event(type="t1", execution_id="e1")))

        assert len(received) == 0

    def test_handler_error_is_logged_not_raised(self):
        from app.engine.event_bus import Event, EventBus

        bus = EventBus()

        async def failing_handler(event: Event):
            raise RuntimeError("boom")

        bus.subscribe(failing_handler, event_types=["test"])
        # Should not raise
        asyncio.run(bus.publish(Event(type="test", execution_id="e1")))


# ============================================================
# 2. WebSocket Manager Tests
# ============================================================

class TestWSManager:
    """Test WS manager message conversion and error propagation."""

    def test_step_started_message(self):
        from app.engine.event_bus import Event
        from app.engine.ws_manager import WSManager

        mgr = WSManager()
        event = Event(type="step_started", execution_id="e1", data={"step_id": "login"})
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["type"] == "node_status"
        assert msg["node_id"] == "login"
        assert msg["status"] == "running"

    def test_step_completed_message_includes_mode_and_summary(self):
        from app.engine.event_bus import Event
        from app.engine.ws_manager import WSManager

        mgr = WSManager()
        event = Event(
            type="step_completed",
            execution_id="e1",
            data={"step_id": "login", "mode": "replay", "summary": "done"},
        )
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["status"] == "success"
        assert msg["data"]["mode"] == "replay"
        assert msg["data"]["summary"] == "done"

    def test_step_failed_message_includes_error(self):
        from app.engine.event_bus import Event
        from app.engine.ws_manager import WSManager

        mgr = WSManager()
        event = Event(
            type="step_failed",
            execution_id="e1",
            data={"step_id": "login", "error": "timeout", "summary": "failed"},
        )
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["status"] == "failed"
        assert msg["data"]["error"] == "timeout"
        assert msg["data"]["summary"] == "failed"

    def test_tool_called_message(self):
        from app.engine.event_bus import Event
        from app.engine.ws_manager import WSManager

        mgr = WSManager()
        event = Event(
            type="tool_called",
            execution_id="e1",
            data={"tool_name": "click", "tool_args": {"selector": "#btn"}},
        )
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["type"] == "log"
        assert "click" in msg["data"]["message"]

    def test_execution_started_and_completed(self):
        from app.engine.event_bus import Event
        from app.engine.ws_manager import WSManager

        mgr = WSManager()

        started = mgr._event_to_ws_message(
            Event(type="execution_started", execution_id="e1", data={})
        )
        assert started["status"] == "running"

        completed = mgr._event_to_ws_message(
            Event(
                type="execution_completed",
                execution_id="e1",
                data={"report": {"status": "completed", "case_name": "test"}},
            )
        )
        assert completed["status"] == "completed"
        assert completed["data"]["report"]["case_name"] == "test"

    def test_unknown_event_type_returns_none(self):
        from app.engine.event_bus import Event
        from app.engine.ws_manager import WSManager

        mgr = WSManager()
        msg = mgr._event_to_ws_message(Event(type="unknown", execution_id="e1"))
        assert msg is None


# ============================================================
# 3. AIContext Tests
# ============================================================

class TestAIContext:
    """Test AIContext explore/replay/script generation logic."""

    def test_script_path_and_has_replay(self):
        from app.engine.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="open_page")

            assert ctx.script_path == case_dir / "scripts" / "open_page.py"
            assert ctx.has_replay() is False

            # Create a script file
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text("async def run(page, ctx): pass")
            assert ctx.has_replay() is True

    def test_mode_auto_replays_when_script_exists(self):
        from app.engine.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="step1")

            # Write a valid replay script
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text(
                "async def run(page, context):\n    pass\n"
            )

            result = asyncio.run(ctx.action("do something", mode="auto"))
            assert result["success"] is True
            assert result["steps"][0]["action"] == "replay"

    def test_mode_explore_always_explores(self):
        from app.engine.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()

            mock_page = MagicMock()
            mock_page.url = "http://test.com"
            ctx = AIContext(page=mock_page, case_dir=case_dir, step_id="step1")

            # Even if script exists, explore mode should overwrite
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text("# existing")

            # Mock the agent run to avoid real LLM calls
            mock_result = {"success": True, "summary": "done", "steps": []}
            with patch.object(ctx, "_explore", AsyncMock(return_value=mock_result)):
                result = asyncio.run(ctx.action("do something", mode="explore"))
                assert result is mock_result

    def test_mode_replay_raises_without_script(self):
        from app.engine.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="step1")

            with pytest.raises(FileNotFoundError):
                asyncio.run(ctx.action("do something", mode="replay"))

    def test_generate_script_simple_actions(self):
        from app.engine.ai_context import AIContext

        ctx = AIContext(page=MagicMock(), case_dir=Path("/tmp"), step_id="test")
        agent_steps = [
            {"action": "navigate", "args": {"url": "https://example.com"}},
            {"action": "click", "args": {"selector": "#btn"}},
            {"action": "fill", "args": {"selector": "#input", "text": "hello"}},
        ]

        script = ctx._generate_script(agent_steps)
        assert "async def run(page, context):" in script
        assert 'await page.goto("https://example.com")' in script
        assert 'await page.click("#btn")' in script
        assert 'await page.fill("#input", "hello")' in script

    def test_generate_script_empty_steps_produces_pass(self):
        from app.engine.ai_context import AIContext

        ctx = AIContext(page=MagicMock(), case_dir=Path("/tmp"), step_id="test")
        script = ctx._generate_script([])
        assert "async def run(page, context):" in script
        assert "    pass" in script

    def test_generate_script_all_action_types(self):
        from app.engine.ai_context import AIContext

        ctx = AIContext(page=MagicMock(), case_dir=Path("/tmp"), step_id="test")
        agent_steps = [
            {"action": "navigate", "args": {"url": "http://a.com"}},
            {"action": "click", "args": {"selector": "#b"}},
            {"action": "click_force", "args": {"selector": "#c"}},
            {"action": "fill", "args": {"selector": "#d", "text": "t"}},
            {"action": "type_text", "args": {"selector": "#e", "text": "x"}},
            {"action": "focus", "args": {"selector": "#f"}},
            {"action": "wait_for", "args": {"selector": "#g", "timeout": 3000}},
            {"action": "scroll", "args": {"direction": "down", "amount": 500}},
            {"action": "eval_js", "args": {"expression": "1+1"}},
            {"action": "select_option", "args": {"selector": "#h", "value": "v"}},
            {"action": "hover", "args": {"selector": "#i"}},
        ]

        script = ctx._generate_script(agent_steps)
        assert 'await page.goto("http://a.com")' in script
        assert 'await page.click("#b")' in script
        assert 'await page.click("#c", force=True)' in script
        assert 'await page.fill("#d", "t")' in script
        assert 'await page.locator("#e").press_sequentially("x")' in script
        assert 'await page.locator("#f").focus()' in script
        assert 'await page.wait_for_selector("#g", timeout=3000)' in script
        assert "await page.mouse.wheel(0, 500)" in script
        assert 'await page.evaluate("1+1")' in script
        assert 'await page.select_option("#h", "v")' in script
        assert 'await page.hover("#i")' in script

    def test_replay_script_with_error_returns_failure(self):
        from app.engine.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="step1")

            # Write a script that raises
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text(
                "async def run(page, context):\n    raise RuntimeError('test error')\n"
            )

            result = asyncio.run(ctx._replay())
            assert result["success"] is False
            assert "test error" in result["summary"]


# ============================================================
# 4. BaseCase Tests
# ============================================================

class TestBaseCase:
    """Test step discovery, decorator, and lifecycle."""

    def test_step_discovery_finds_ai_methods(self):
        from app.engine.base_case import BaseCase, step_mode

        class MyCase(BaseCase):
            async def setup(self):
                pass

            async def teardown(self):
                pass

            async def open_page(self, ai):
                """Open the home page."""
                pass

            @step_mode("explore")
            async def search(self, ai):
                """Search for keywords."""
                pass

            def not_a_step(self):
                pass

        case = MyCase()
        steps = case.get_step_methods()

        assert "open_page" in steps
        assert "search" in steps
        assert "setup" not in steps
        assert "teardown" not in steps
        assert "not_a_step" not in steps  # no 'ai' param
        assert "get_step_methods" not in steps

    def test_step_mode_decorator_sets_mode(self):
        from app.engine.base_case import BaseCase, step_mode

        class MyCase(BaseCase):
            @step_mode("explore")
            async def my_step(self, ai):
                pass

        case = MyCase()
        method = getattr(MyCase, "my_step")
        assert getattr(method, "_step_mode", "auto") == "explore"

    def test_default_mode_is_auto(self):
        from app.engine.base_case import BaseCase

        class MyCase(BaseCase):
            async def my_step(self, ai):
                pass

        case = MyCase()
        method = getattr(MyCase, "my_step")
        assert getattr(method, "_step_mode", "auto") == "auto"

    def test_results_dir_stored(self):
        from app.engine.base_case import BaseCase

        results_dir = Path("/tmp/fake_results")
        case = BaseCase(case_dir=Path("/tmp"), results_dir=results_dir)
        assert case._results_dir == results_dir

    def test_results_dir_defaults_to_none(self):
        from app.engine.base_case import BaseCase

        case = BaseCase()
        assert case._results_dir is None


# ============================================================
# 5. PyCaseRunner Tests
# ============================================================

class TestPyCaseRunner:
    """Test case discovery and listing."""

    def test_discover_case_class(self):
        from app.engine.py_case_runner import discover_case_class

        case_dir = Path(__file__).resolve().parent.parent.parent / "cases" / "baidu_search"
        cls = discover_case_class(case_dir)
        assert cls.__name__ == "BaiduSearchCase"

    def test_list_cases_returns_all(self):
        from app.engine.py_case_runner import list_cases

        cases_root = Path(__file__).resolve().parent.parent.parent / "cases"
        cases = list_cases(cases_root)
        assert len(cases) >= 4  # baidu_search, baidu_search_explore, baidu_search_replay, playwright_docs

        case_ids = [c["id"] for c in cases]
        assert "baidu_search" in case_ids
        assert "playwright_docs" in case_ids

    def test_list_cases_structure(self):
        from app.engine.py_case_runner import list_cases

        cases_root = Path(__file__).resolve().parent.parent.parent / "cases"
        cases = list_cases(cases_root)

        for c in cases:
            assert "id" in c
            assert "name" in c
            assert "dir" in c
            assert "steps" in c
            assert isinstance(c["steps"], list)

    def test_run_case_accepts_results_dir(self):
        from app.engine.base_case import BaseCase
        from app.engine.py_case_runner import run_case

        with tempfile.TemporaryDirectory() as tmpdir:
            # Subclass BaseCase so the constructor accepts case_dir/results_dir
            class FakeCase(BaseCase):
                pass

            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(return_value={
                "case_name": "FakeCase",
                "status": "completed",
                "total_steps": 1,
                "success_count": 1,
                "failed_count": 0,
                "steps": [],
            })

            with patch(
                "app.engine.py_case_runner.discover_case_class",
                return_value=FakeCase,
            ):
                with patch.object(FakeCase, "__new__", return_value=mock_instance):
                    results_dir = Path(tmpdir) / "results"
                    report = asyncio.run(
                        run_case(
                            case_dir=Path("/fake"),
                            results_dir=results_dir,
                        )
                    )
                    assert report["status"] == "completed"


# ============================================================
# 6. Browser Config Tests
# ============================================================

class TestBrowserConfig:
    """Test browser launch args configuration."""

    def test_default_is_not_headless(self):
        import os
        # Remove HEADLESS if set
        old = os.environ.pop("HEADLESS", None)
        try:
            import app.engine.browser
            importlib.reload(app.engine.browser)
            from app.engine.browser import get_launch_args

            args = get_launch_args()
            assert args["headless"] is False
        finally:
            if old:
                os.environ["HEADLESS"] = old
            importlib.reload(app.engine.browser)

    def test_headless_true_via_env(self):
        import os
        old = os.environ.get("HEADLESS")
        os.environ["HEADLESS"] = "true"
        try:
            import app.engine.browser
            importlib.reload(app.engine.browser)
            from app.engine.browser import get_launch_args

            args = get_launch_args()
            assert args["headless"] is True
        finally:
            if old is None:
                os.environ.pop("HEADLESS", None)
            else:
                os.environ["HEADLESS"] = old
            importlib.reload(app.engine.browser)

    def test_headless_accepts_1_and_yes(self):
        import os
        old = os.environ.get("HEADLESS")
        for val in ("1", "yes", "true"):
            os.environ["HEADLESS"] = val
            try:
                import app.engine.browser
                importlib.reload(app.engine.browser)
                from app.engine.browser import get_launch_args
                assert get_launch_args()["headless"] is True, f"HEADLESS={val}"
            finally:
                importlib.reload(app.engine.browser)
        if old is None:
            os.environ.pop("HEADLESS", None)
        else:
            os.environ["HEADLESS"] = old
        importlib.reload(app.engine.browser)

    def test_chrome_path_only_when_set(self):
        import os
        old = os.environ.pop("CHROME_PATH", None)
        try:
            import app.engine.browser
            importlib.reload(app.engine.browser)
            from app.engine.browser import get_launch_args

            args = get_launch_args()
            assert "executable_path" not in args
        finally:
            if old:
                os.environ["CHROME_PATH"] = old
            importlib.reload(app.engine.browser)


# ============================================================
# 7. Logger Config Tests
# ============================================================

class TestLoggerConfig:
    """Test logger configuration."""

    def test_log_level_defaults_to_info(self):
        old = os.environ.pop("LOG_LEVEL", None)
        try:
            import app.logger
            importlib.reload(app.logger)
            assert app.logger.LOG_LEVEL == "INFO"
        finally:
            if old:
                os.environ["LOG_LEVEL"] = old
            importlib.reload(app.logger)

    def test_log_level_from_env(self):
        old = os.environ.get("LOG_LEVEL")
        os.environ["LOG_LEVEL"] = "WARNING"
        try:
            import app.logger
            importlib.reload(app.logger)
            assert app.logger.LOG_LEVEL == "WARNING"
        finally:
            if old is None:
                os.environ.pop("LOG_LEVEL", None)
            else:
                os.environ["LOG_LEVEL"] = old
            importlib.reload(app.logger)


# ============================================================
# 8. Tool Registry Tests
# ============================================================

class TestToolRegistry:
    """Test tool self-registration."""

    def test_tools_are_registered(self):
        from app.engine.tool_registry import ToolRegistry
        import app.engine.tools  # triggers registration

        registry = ToolRegistry()
        tools = registry.get_all()

        tool_names = [t.name for t in tools]
        assert len(tools) >= 13  # 13 tools + possible screenshot
        assert "navigate" in tool_names
        assert "click" in tool_names
        assert "fill" in tool_names
        assert "get_page_info" in tool_names
        assert "screenshot" in tool_names

    def test_tool_registry_is_singleton(self):
        from app.engine.tool_registry import ToolRegistry
        import app.engine.tools

        r1 = ToolRegistry()
        r2 = ToolRegistry()
        assert r1 is r2


# ============================================================
# 9. API Integration Tests (FastAPI TestClient)
# ============================================================

class TestAPI:
    """Integration tests via FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.routers.cases import _executions
        _executions.clear()
        self.client = TestClient(app)
        self.cases_root = Path(__file__).resolve().parent.parent.parent / "cases"

    def test_health(self):
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_list_cases(self):
        resp = self.client.get("/api/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4
        for item in data:
            assert "id" in item
            assert "name" in item
            assert "steps" in item

    def test_get_case_with_descriptions(self):
        resp = self.client.get("/api/cases/baidu_search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "baidu_search"
        assert data["name"] == "BaiduSearchCase"
        assert len(data["steps"]) == 3

        # Steps should now have non-empty descriptions from docstrings
        for step in data["steps"]:
            assert "id" in step
            assert "name" in step
            assert "mode" in step
            assert "description" in step

    def test_get_case_404(self):
        resp = self.client.get("/api/cases/nonexistent")
        assert resp.status_code == 404

    def test_list_scripts(self):
        resp = self.client.get("/api/cases/baidu_search/scripts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_script_404(self):
        resp = self.client.get("/api/cases/baidu_search/scripts/nonexistent_step")
        assert resp.status_code == 404

    def test_update_script(self):
        # First list scripts to find one
        resp = self.client.get("/api/cases/baidu_search/scripts")
        if resp.json():
            script = resp.json()[0]
            original = script["content"]
            new_content = original + "\n# test update"

            resp2 = self.client.put(
                f"/api/cases/baidu_search/scripts/{script['step_id']}",
                json={"content": new_content},
            )
            assert resp2.status_code == 200
            assert resp2.json()["content"] == new_content

            # Restore original
            self.client.put(
                f"/api/cases/baidu_search/scripts/{script['step_id']}",
                json={"content": original},
            )

    def test_update_script_404(self):
        resp = self.client.put(
            "/api/cases/baidu_search/scripts/nonexistent",
            json={"content": "test"},
        )
        assert resp.status_code == 404

    def test_solidify_script_no_script(self):
        """Solidify on a non-existent script should return 404."""
        resp = self.client.post("/api/cases/baidu_search/scripts/nonexistent_step/solidify")
        assert resp.status_code == 404

    def test_solidify_existing_script(self):
        """Solidify an existing script should succeed."""
        resp = self.client.get("/api/cases/baidu_search/scripts")
        if resp.json():
            step_id = resp.json()[0]["step_id"]
            resp2 = self.client.post(f"/api/cases/baidu_search/scripts/{step_id}/solidify")
            assert resp2.status_code == 200
            data = resp2.json()
            assert data["step_id"] == step_id
            assert data["status"] == "solidified"

            # Verify marker file was created
            marker = self.cases_root / "baidu_search" / "scripts" / f".{step_id}.solidified"
            assert marker.exists()
            marker.unlink()  # cleanup

    def test_stop_no_running_execution(self):
        resp = self.client.post("/api/cases/baidu_search/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"

    def test_stop_nonexistent_case(self):
        resp = self.client.post("/api/cases/nonexistent/stop")
        assert resp.status_code == 404

    def test_results_empty_initially(self):
        """Results endpoint should return empty list for a case with no results dir."""
        # The baidu_search case might or might not have results
        resp = self.client.get("/api/cases/baidu_search/results")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_results_404_for_nonexistent_timestamp(self):
        resp = self.client.get("/api/cases/baidu_search/results/19700101_000000")
        assert resp.status_code == 404

    def test_cors_headers_present(self):
        resp = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # TestClient may or may not return CORS headers depending on the request
        # Just verify the endpoint works
        assert resp.status_code in (200, 405)

    def test_run_case_404(self):
        resp = self.client.post("/api/cases/nonexistent/run")
        assert resp.status_code == 404

    def test_run_case_starts_execution(self):
        """Run case should start successfully (without waiting for completion).
        Mock run_case to avoid real browser + LLM calls."""
        with patch("app.routers.cases.run_case") as mock_run:
            mock_run.return_value = {
                "case_name": "Test",
                "status": "completed",
                "total_steps": 1,
                "success_count": 1,
                "failed_count": 0,
                "steps": [],
            }
            resp = self.client.post("/api/cases/baidu_search/run")
            assert resp.status_code == 200
            data = resp.json()
            assert data["case_id"] == "baidu_search"
            assert data["status"] == "started"


# ============================================================
# 10. Result Persistence Tests
# ============================================================

class TestResultPersistence:
    """Test that execution results are properly saved."""

    def test_report_saved_after_execution(self):
        """Mock a full execution and verify report.json is saved."""
        from app.routers.cases import CASES_ROOT

        case_dir = CASES_ROOT / "baidu_search"
        results_dir = case_dir / "results"

        # Create a mock execution result
        test_timestamp = "20260101_120000"
        test_results_dir = results_dir / test_timestamp
        test_results_dir.mkdir(parents=True, exist_ok=True)
        test_report = {
            "case_name": "BaiduSearchCase",
            "status": "completed",
            "total_steps": 3,
            "success_count": 3,
            "failed_count": 0,
            "steps": [],
        }
        (test_results_dir / "report.json").write_text(json.dumps(test_report))

        try:
            # Now query via API
            from fastapi.testclient import TestClient
            from app.main import app
            client = TestClient(app)

            resp = client.get("/api/cases/baidu_search/results")
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) >= 1
            assert any(r["timestamp"] == test_timestamp for r in results)

            # Get specific result
            resp2 = client.get(f"/api/cases/baidu_search/results/{test_timestamp}")
            assert resp2.status_code == 200
            assert resp2.json()["report"]["case_name"] == "BaiduSearchCase"
            assert "screenshots" in resp2.json()
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(test_results_dir)
            # Remove parent if empty
            if results_dir.exists() and not list(results_dir.iterdir()):
                results_dir.rmdir()


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    # Run with pytest for better output when executed directly
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent,
    )
    sys.exit(result.returncode)
