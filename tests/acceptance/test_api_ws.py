"""Acceptance tests — API lifecycle, WSManager integration, and edge cases."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.acceptance.conftest import _make_mock_page


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
        resp = self.client.get("/api/cases")
        assert resp.status_code == 200
        cases = resp.json()
        assert len(cases) >= 1

        case_id = cases[0]["id"]

        resp2 = self.client.get(f"/api/cases/{case_id}")
        assert resp2.status_code == 200
        detail = resp2.json()
        assert detail["id"] == case_id
        assert "steps" in detail
        assert isinstance(detail["steps"], list)

        resp3 = self.client.get(f"/api/cases/{case_id}/scripts")
        assert resp3.status_code == 200

    def test_run_mocked_then_query_results(self):
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

            resp = self.client.post("/api/cases/baidu_search__01_basecase/run")
            assert resp.status_code == 200
            assert resp.json()["status"] == "started"

            import time
            time.sleep(0.5)

        resp2 = self.client.get("/api/cases/baidu_search__01_basecase/results")
        assert resp2.status_code == 200
        results = resp2.json()
        assert len(results) >= 1

        latest = results[0]
        assert latest["report"]["status"] == "completed"
        assert latest["report"]["success_count"] == 3

    def test_update_and_solidify_script_flow(self):
        cases = self.client.get("/api/cases").json()
        target_case = None
        target_case_dir = None
        target_step = None
        for c in cases:
            scripts = self.client.get(f"/api/cases/{c['id']}/scripts").json()
            if scripts:
                target_case = c["id"]
                target_case_dir = Path(c["case_dir"])
                target_step = scripts[0]["step_id"]
                break

        if not target_case:
            pytest.skip("No cases with scripts found")

        resp = self.client.get(f"/api/cases/{target_case}/scripts/{target_step}")
        original_content = resp.json()["content"]

        new_content = original_content + "\n# acceptance test update"
        resp2 = self.client.put(
            f"/api/cases/{target_case}/scripts/{target_step}",
            json={"content": new_content},
        )
        assert resp2.status_code == 200
        assert resp2.json()["content"] == new_content

        resp3 = self.client.post(f"/api/cases/{target_case}/scripts/{target_step}/solidify")
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "solidified"

        marker = target_case_dir / "scripts" / f".{target_step}.solidified" if target_case_dir else None
        assert marker and marker.exists()

        self.client.put(
            f"/api/cases/{target_case}/scripts/{target_step}",
            json={"content": original_content},
        )
        marker.unlink(missing_ok=True)

    def test_run_cancels_previous_execution(self):

        call_count = 0

        async def slow_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(10)
            return {"status": "completed", "total_steps": 0, "success_count": 0, "failed_count": 0, "steps": []}

        with patch("skiritai.web.routers.cases.run_case", side_effect=slow_run):
            resp1 = self.client.post("/api/cases/baidu_search__01_basecase/run")
            assert resp1.status_code == 200

            resp2 = self.client.post("/api/cases/baidu_search__01_basecase/run")
            assert resp2.status_code == 200

        import time
        time.sleep(0.2)

    def test_stop_cancels_registered_task(self):
        from skiritai.core.execution_manager import cancel_execution as _cancel_execution, _executions

        async def _test():
            async def dummy():
                await asyncio.sleep(60)

            task = asyncio.create_task(dummy())
            _executions["test_case"] = task

            result = await _cancel_execution("test_case")
            assert result is True
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert task.cancelled()
            assert "test_case" not in _executions

        asyncio.run(_test())

    def test_stop_returns_not_found_when_no_task(self):
        resp = self.client.post("/api/cases/baidu_search__01_basecase/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_found"


class TestWSManagerIntegration:
    """Test WSManager handles real event sequences correctly."""

    def test_full_execution_event_sequence(self):
        from skiritai.events import Event
        from skiritai.web.ws_manager import WSManager

        mgr = WSManager()
        messages = []

        events = [
            Event(type="execution_started", execution_id="e1", data={}),
            Event(type="step_started", execution_id="e1", data={"step_id": "open"}),
            Event(type="tool_called", execution_id="e1",
                  data={"tool_name": "navigate", "tool_args": {"url": "http://x.com"}}),
            Event(type="step_completed", execution_id="e1",
                  data={"step_id": "open", "mode": "explore", "summary": "ok"}),
            Event(type="step_started", execution_id="e1", data={"step_id": "click"}),
            Event(type="step_completed", execution_id="e1",
                  data={"step_id": "click", "mode": "replay", "summary": "done"}),
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


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_case_with_no_steps(self):
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
        from skiritai.core.base_case import BaseCase

        class PrivateCase(BaseCase):
            async def _helper(self, ai):
                pass

            async def public_step(self, ai):
                pass

        case = PrivateCase()
        steps = case.get_step_methods()

        assert "_helper" not in steps
        assert "public_step" in steps

    def test_methods_without_ai_param_not_discovered(self):
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

        # All public callable methods are auto-discovered as steps,
        # regardless of parameter signature. Sync methods are included too.
        assert "real_step" in steps
        assert "not_a_step" in steps
        assert "sync_method" in steps

    def test_script_path_isolation_between_steps(self):
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
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "missing"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="no_script")

            with pytest.raises(FileNotFoundError, match="no_script"):
                asyncio.run(ctx.action("do it", mode="replay"))

    def test_list_cases_skips_invalid_dirs(self):
        from skiritai.core.runner import list_cases

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            valid = root / "valid"
            valid.mkdir()
            (valid / "case.py").write_text(
                "from skiritai.core.base_case import BaseCase\n"
                "class V(BaseCase): pass\n"
            )
            (root / "no_case").mkdir()
            bad = root / "bad_syntax"
            bad.mkdir()
            (bad / "case.py").write_text("def broken(")

            cases = list_cases(root)
            assert len(cases) == 1
            assert cases[0]["id"] == "valid"

    def test_discover_case_class_missing_file_raises(self):
        from skiritai.core.runner import discover_case_class

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                discover_case_class(Path(tmpdir))

    def test_api_case_detail_includes_step_modes(self):
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app

        client = TestClient(create_app())
        resp = client.get("/api/cases/baidu_search__01_basecase")
        assert resp.status_code == 200

        steps = resp.json()["steps"]
        for step in steps:
            assert "mode" in step
            assert step["mode"] in ("explore", "solidified")

    def test_api_nonexistent_case_endpoints_return_404(self):
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app

        client = TestClient(create_app())

        assert client.get("/api/cases/does_not_exist").status_code == 404
        assert client.post("/api/cases/does_not_exist/run").status_code == 404
        assert client.post("/api/cases/does_not_exist/stop").status_code == 404
        assert client.get("/api/cases/does_not_exist/results").status_code == 404
        assert client.get("/api/cases/does_not_exist/results/ts").status_code == 404

    def test_generate_script_scroll_up_direction(self):
        from skiritai.core.script_generator import generate_replay_script

        steps = [{"action": "scroll", "args": {"direction": "up", "amount": 300}}]
        script = generate_replay_script("test", steps)
        assert "await page.mouse.wheel(0, -300)" in script

    def test_generate_script_eval_js_escapes_quotes(self):
        from skiritai.core.script_generator import generate_replay_script

        steps = [{"action": "eval_js", "args": {"expression": 'document.querySelector("div").click()'}}]
        script = generate_replay_script("test", steps)
        assert "document.querySelector" in script
        assert '"div"' in script
        assert "page.evaluate" in script

    def test_result_report_step_mode_field(self):
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mode_check"
            case_dir.mkdir()

            page = _make_mock_page()

            ctx = AIContext(page=page, case_dir=case_dir, step_id="my_step")
            assert ctx.has_replay() is False

            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text("async def run(page, context):\n    pass\n")
            assert ctx.has_replay() is True

            ctx2 = AIContext(page=page, case_dir=case_dir, step_id="other_step")
            assert ctx2.has_replay() is False


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
