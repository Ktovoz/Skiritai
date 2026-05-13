"""Functional tests for yaml_runner — step execution with mocked browser/AI."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_session(page=None):
    """Create a mock BrowserSession."""
    from skiritai.core._session import BrowserSession

    session = MagicMock(spec=BrowserSession)
    session.page = page or MagicMock()
    session.started_at = 1000.0
    session.start = AsyncMock()
    session.stop = AsyncMock()
    return session


def _make_case_yaml(tmp_path: Path, content: str) -> Path:
    """Write case.yaml and return the directory."""
    (tmp_path / "case.yaml").write_text(content, encoding="utf-8")
    return tmp_path


# ============================================================
# 1. Step Executor Tests
# ============================================================

class TestExecAction:
    """Test _exec_action step executor."""

    async def test_success(self):
        from skiritai.core.yaml_runner import _exec_action

        mock_ai = AsyncMock()
        mock_ai.action.return_value = {"success": True, "summary": "did it"}
        mock_ai.has_replay = MagicMock(return_value=False)

        status, entry = await _exec_action(mock_ai, "open page")
        assert status == "success"
        assert entry["status"] == "success"
        assert entry["summary"] == "did it"

    async def test_failure(self):
        from skiritai.core.yaml_runner import _exec_action

        mock_ai = AsyncMock()
        mock_ai.action.return_value = {"success": False, "summary": "failed"}
        mock_ai.has_replay = MagicMock(return_value=False)

        status, entry = await _exec_action(mock_ai, "bad action")
        assert status == "failed"
        assert entry["status"] == "failed"

    async def test_replay_mode(self):
        from skiritai.core.yaml_runner import _exec_action

        mock_ai = AsyncMock()
        mock_ai.action.return_value = {"success": True, "summary": "replayed"}
        mock_ai.has_replay = MagicMock(return_value=True)

        status, entry = await _exec_action(mock_ai, "action")
        assert entry["mode"] == "replay"


class TestExecVerify:
    """Test _exec_verify step executor."""

    async def test_passed(self):
        from skiritai.core.yaml_runner import _exec_verify

        mock_ai = AsyncMock()
        mock_ai.verify.return_value = {"passed": True, "reason": "looks good"}

        status, entry = await _exec_verify(mock_ai, "check title")
        assert status == "passed"
        assert entry["assertion"] == "check title"

    async def test_failed(self):
        from skiritai.core.yaml_runner import _exec_verify

        mock_ai = AsyncMock()
        mock_ai.verify.return_value = {"passed": False, "reason": "not found"}

        status, entry = await _exec_verify(mock_ai, "check title")
        assert status == "failed"


class TestExecScreenshot:
    """Test _exec_screenshot step executor."""

    async def test_success(self):
        from skiritai.core.yaml_runner import _exec_screenshot

        mock_ai = AsyncMock()
        mock_ai.screenshot.return_value = "/tmp/shot.png"

        status, entry = await _exec_screenshot(mock_ai, "result")
        assert status == "success"
        assert entry["screenshot"] == "/tmp/shot.png"


class TestExecAnalyze:
    """Test _exec_analyze step executor."""

    async def test_success(self):
        from skiritai.core.yaml_runner import _exec_analyze

        mock_ai = AsyncMock()
        mock_ai.analyze_page.return_value = {"title": "Test"}

        status, entry = await _exec_analyze(mock_ai, "")
        assert status == "success"


class TestExecPageInfo:
    """Test _exec_page_info step executor."""

    async def test_success(self):
        from skiritai.core.yaml_runner import _exec_page_info

        mock_ai = AsyncMock()
        mock_ai.get_page_info.return_value = "Title: Test"

        status, entry = await _exec_page_info(mock_ai, "")
        assert status == "success"
        assert entry["page_info"] == "Title: Test"


# ============================================================
# 2. run_yaml_case Integration Tests (mocked browser)
# ============================================================

class TestRunYamlCase:
    """Test run_yaml_case() full execution with mocked browser and AI."""

    def _make_mock_ai(self):
        """Create a mock AIContext with sensible defaults.

        has_replay() is a sync method on AIContext, so we mock it as a regular Mock.
        """
        mock_ai = AsyncMock()
        mock_ai.has_replay = MagicMock(return_value=False)
        mock_ai._step_started_at = 0
        mock_ai._step_elapsed = 0.5
        mock_ai._page_analysis = None
        mock_ai._page_info = None
        mock_ai.step_id = "mock_step"
        mock_ai.copy_for_step = MagicMock(return_value=mock_ai)
        return mock_ai

    async def test_simple_two_step_case(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Simple
steps:
  - action: open page
  - verify: page loaded
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    mock_ai.verify.return_value = {"passed": True, "reason": "good"}
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir)

        assert report["status"] == "completed"
        assert report["total_steps"] == 2
        assert report["success_count"] == 2
        assert report["failed_count"] == 0
        assert report["source"] == "yaml"
        assert len(report["steps"]) == 2

    async def test_failed_step_aborts(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Abort Test
steps:
  - action: open page
  - action: will fail
  - action: never reached
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.side_effect = [
                        {"success": True, "summary": "ok"},
                        {"success": False, "summary": "fail"},
                    ]
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir)

        assert report["status"] == "failed"
        assert report["aborted"] is True
        assert len(report["steps"]) == 2  # third step never reached

    async def test_skip_policy_continues(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Skip Test
steps:
  - action: will fail
    on_failure: skip
  - action: continues
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.side_effect = [
                        {"success": False, "summary": "fail"},
                        {"success": True, "summary": "ok"},
                    ]
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir)

        assert len(report["steps"]) == 2
        assert report["steps"][0]["status"] == "failed"
        assert report["steps"][1]["status"] == "success"
        assert "aborted" not in report

    async def test_exception_in_step(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Error Test
steps:
  - action: will crash
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.side_effect = RuntimeError("boom")
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir)

        assert report["status"] == "failed"
        assert report["steps"][0]["error"] == "boom"

    async def test_custom_execution_id(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: ID Test
steps:
  - action: test
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    MockAI.return_value = mock_ai

                    with patch("skiritai.core.yaml_runner.event_bus") as mock_bus:
                        mock_bus.publish = AsyncMock()
                        report = await run_yaml_case(case_dir, execution_id="custom_id")

        assert report["case_name"] == "ID Test"

    async def test_report_saved(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Report Test
steps:
  - action: test
""")
        mock_session = _make_mock_session()
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir, results_dir=results_dir)

        reports = list((results_dir / "test_results").rglob("report.json"))
        assert len(reports) == 1

    async def test_step_with_name(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Named Steps
steps:
  - name: my_first_step
    action: open page
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir)

        assert report["steps"][0]["step_id"] == "my_first_step"

    async def test_unknown_step_type_skipped(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Unknown Type
steps:
  - unknown_type: something
  - action: valid step
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    MockAI.return_value = mock_ai

                    report = await run_yaml_case(case_dir)

        assert len(report["steps"]) == 2
        assert report["steps"][0]["status"] == "skipped"
        assert report["steps"][1]["status"] == "success"

    async def test_browser_lifecycle_called(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: Lifecycle
steps:
  - action: test
""")
        mock_session = _make_mock_session()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    MockAI.return_value = mock_ai

                    await run_yaml_case(case_dir)

        mock_session.start.assert_called_once()
        mock_session.stop.assert_called_once()

    async def test_start_url_navigation(self, tmp_path: Path):
        from skiritai.core.yaml_runner import run_yaml_case

        case_dir = _make_case_yaml(tmp_path, """
name: With URL
url: https://example.com
steps:
  - action: test
""")
        mock_session = _make_mock_session()
        mock_session.page.goto = AsyncMock()
        mock_session.page.wait_for_load_state = AsyncMock()

        with patch("skiritai.core.yaml_runner.BrowserSession", return_value=mock_session):
            with patch("skiritai.core.agent_loop.register_all_tools"):
                with patch("skiritai.core.yaml_runner.AIContext") as MockAI:
                    mock_ai = self._make_mock_ai()
                    mock_ai.action.return_value = {"success": True, "summary": "ok"}
                    MockAI.return_value = mock_ai

                    await run_yaml_case(case_dir)

        mock_session.page.goto.assert_called_once_with("https://example.com")
        mock_session.page.wait_for_load_state.assert_called_once_with("networkidle")


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
