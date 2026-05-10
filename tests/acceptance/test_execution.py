"""Acceptance tests — end-to-end case execution with mocked LLM/browser."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tests.acceptance.conftest import _make_mock_page


class TestEndToEndExecution:
    """Full case execution with mocked AI agent."""

    def test_single_step_explore_success(self):
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
        assert report["failed_count"] == 2
        assert "aaa_first" in call_log
        assert "bbb_fail" in call_log
        assert "ccc_never" not in call_log

    def test_step_exception_stops_execution(self):
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


class TestStepModeBehavior:
    """Verify @step_mode decorator controls explore/replay/auto behavior."""

    def test_explore_mode_always_calls_agent(self):
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

        scripts_dir = case._case_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "forced_explore.py").write_text("# old script")

        mock_result = {"success": True, "summary": "explored", "steps": [
            {"action": "navigate", "args": {"url": "http://x.com"}}
        ]}

        with patch("skiritai.core.ai_context.run_agent", AsyncMock(return_value=mock_result)) as mock_agent:
            report = asyncio.run(case.run())

        mock_agent.assert_called_once()
        new_content = (scripts_dir / "forced_explore.py").read_text()
        assert "old script" not in new_content
        assert "async def run" in new_content
        assert report["status"] == "completed"

    def test_replay_mode_uses_saved_script(self):
        import tempfile
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
        import tempfile
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

        mock_agent.assert_called_once()
        assert report["status"] == "completed"


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
