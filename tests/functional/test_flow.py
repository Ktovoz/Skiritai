"""Functional tests for flow.py — FlowAI internals and report generation."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_session(page=None):
    """Create a mock BrowserSession with a mock page."""
    from skiritai.core._session import BrowserSession

    session = MagicMock(spec=BrowserSession)
    session.page = page or MagicMock()
    session.started_at = 1000.0
    session.start = AsyncMock()
    session.stop = AsyncMock()
    return session


# ============================================================
# 1. FlowAI Internal Tests
# ============================================================

class TestFlowAIInternals:
    """Test FlowAI step counting and context management."""

    def test_next_step_id_auto(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)
        assert ai._next_step_id() == "step_1"
        assert ai._next_step_id() == "step_2"
        assert ai._next_step_id() == "step_3"

    def test_next_step_id_with_prefix(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)
        assert ai._next_step_id("verify_") == "verify_1"
        assert ai._next_step_id("ss_") == "ss_2"
        assert ai._next_step_id("analyze_") == "analyze_3"

    def test_initial_state(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, results_dir=Path("/tmp/test"))
        assert ai._step_counter == 0
        assert ai._results == []
        assert ai._screenshots == []
        assert ai._ai is None
        assert ai._max_steps == 20

    def test_custom_max_steps(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, max_steps=5)
        assert ai._max_steps == 5

    def test_ensure_ai_creates_first(self):
        from skiritai.core.flow import FlowAI
        from skiritai.core.ai_context import AIContext

        mock_page = MagicMock()
        session = _make_mock_session(page=mock_page)
        ai = FlowAI(session=session)

        ctx = ai._ensure_ai("step_1")
        assert isinstance(ctx, AIContext)
        assert ai._ai is ctx

    def test_ensure_ai_reuses_same_step(self):
        from skiritai.core.flow import FlowAI

        mock_page = MagicMock()
        session = _make_mock_session(page=mock_page)
        ai = FlowAI(session=session)

        ctx1 = ai._ensure_ai("step_1")
        ctx2 = ai._ensure_ai("step_1")
        assert ctx1 is ctx2

    def test_ensure_ai_creates_new_for_different_step(self):
        from skiritai.core.flow import FlowAI

        mock_page = MagicMock()
        session = _make_mock_session(page=mock_page)
        ai = FlowAI(session=session)

        ctx1 = ai._ensure_ai("step_1")
        ctx2 = ai._ensure_ai("step_2")
        assert ctx1 is not ctx2
        assert ai._ai is ctx2

    def test_advance_ai_creates_new(self):
        from skiritai.core.flow import FlowAI

        mock_page = MagicMock()
        session = _make_mock_session(page=mock_page)
        ai = FlowAI(session=session)

        ctx1 = ai._advance_ai("step_1")
        ctx2 = ai._advance_ai("step_2")
        assert ctx1 is not ctx2
        assert ai._ai is ctx2

    def test_advance_ai_carries_perception_cache(self):
        from skiritai.core.flow import FlowAI

        mock_page = MagicMock()
        session = _make_mock_session(page=mock_page)
        ai = FlowAI(session=session)

        ctx1 = ai._advance_ai("step_1")
        ctx1._page_analysis = {"title": "Test"}
        ctx1._page_info = "page info data"

        ctx2 = ai._advance_ai("step_2")
        assert ctx2._page_analysis == {"title": "Test"}
        assert ctx2._page_info == "page info data"


# ============================================================
# 2. FlowAI Report Tests
# ============================================================

class TestFlowAIReport:
    """Test FlowAI._save_report() logic."""

    def test_no_report_without_results_dir(self, tmp_path: Path):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, results_dir=None)
        ai._results.append({"step_id": "step_1", "status": "success"})
        # Should not raise and should not create any files
        ai._save_report()
        assert not (tmp_path / "test_results").exists()

    def test_no_report_without_results(self, tmp_path: Path):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, results_dir=tmp_path)
        assert ai._results == []
        ai._save_report()
        # No test_results dir created when no results
        assert not (tmp_path / "test_results").exists()

    def test_report_all_success(self, tmp_path: Path):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, results_dir=tmp_path)
        ai._results = [
            {"step_id": "step_1", "status": "success", "type": "action"},
            {"step_id": "verify_2", "status": "passed", "type": "verify"},
        ]
        ai._save_report()

        # Find the report file
        reports = list((tmp_path / "test_results").rglob("report.json"))
        assert len(reports) == 1
        report = json.loads(reports[0].read_text(encoding="utf-8"))
        assert report["status"] == "completed"
        assert report["total_steps"] == 2
        assert report["success_count"] == 2
        assert report["failed_count"] == 0

    def test_report_with_failure(self, tmp_path: Path):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, results_dir=tmp_path)
        ai._results = [
            {"step_id": "step_1", "status": "success", "type": "action"},
            {"step_id": "step_2", "status": "failed", "type": "action"},
        ]
        ai._save_report()

        reports = list((tmp_path / "test_results").rglob("report.json"))
        report = json.loads(reports[0].read_text(encoding="utf-8"))
        assert report["status"] == "failed"
        assert report["success_count"] == 1
        assert report["failed_count"] == 1

    def test_report_case_name_is_flow(self, tmp_path: Path):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session, results_dir=tmp_path)
        ai._results = [{"step_id": "s1", "status": "success"}]
        ai._save_report()

        reports = list((tmp_path / "test_results").rglob("report.json"))
        report = json.loads(reports[0].read_text(encoding="utf-8"))
        assert report["case_name"] == "flow"


# ============================================================
# 3. FlowAI action/verify/screenshot with mocked AIContext
# ============================================================

class TestFlowAIActions:
    """Test FlowAI public API methods with mocked AIContext."""

    async def test_action_records_result(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)

        mock_ai_ctx = AsyncMock()
        mock_ai_ctx.action.return_value = {"success": True, "summary": "did it"}
        mock_ai_ctx.has_replay = MagicMock(return_value=False)
        mock_ai_ctx._step_started_at = 0
        mock_ai_ctx._step_elapsed = 1.0

        with patch.object(ai, "_advance_ai", return_value=mock_ai_ctx):
            with patch("skiritai.core.flow.event_bus") as mock_bus:
                mock_bus.publish = AsyncMock()
                result = await ai.action("do something")

        assert result["success"] is True
        assert len(ai._results) == 1
        assert ai._results[0]["status"] == "success"
        assert ai._results[0]["step_id"] == "step_1"

    async def test_action_records_failure(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)

        mock_ai_ctx = AsyncMock()
        mock_ai_ctx.action.return_value = {"success": False, "summary": "failed"}
        mock_ai_ctx.has_replay = MagicMock(return_value=False)
        mock_ai_ctx._step_started_at = 0
        mock_ai_ctx._step_elapsed = 1.0

        with patch.object(ai, "_advance_ai", return_value=mock_ai_ctx):
            with patch("skiritai.core.flow.event_bus") as mock_bus:
                mock_bus.publish = AsyncMock()
                result = await ai.action("do something bad")

        assert result["success"] is False
        assert ai._results[0]["status"] == "failed"

    async def test_verify_records_result(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)

        mock_ai_ctx = AsyncMock()
        mock_ai_ctx.verify.return_value = {"passed": True, "reason": "looks good"}
        mock_ai_ctx._step_started_at = 0
        mock_ai_ctx._step_elapsed = 0.5

        with patch.object(ai, "_advance_ai", return_value=mock_ai_ctx):
            with patch("skiritai.core.flow.event_bus") as mock_bus:
                mock_bus.publish = AsyncMock()
                result = await ai.verify("check page title")

        assert result["passed"] is True
        assert ai._results[0]["type"] == "verify"
        assert ai._results[0]["assertion"] == "check page title"

    async def test_verify_records_failure(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)

        mock_ai_ctx = AsyncMock()
        mock_ai_ctx.verify.return_value = {"passed": False, "reason": "not found"}
        mock_ai_ctx._step_started_at = 0
        mock_ai_ctx._step_elapsed = 0.5

        with patch.object(ai, "_advance_ai", return_value=mock_ai_ctx):
            with patch("skiritai.core.flow.event_bus") as mock_bus:
                mock_bus.publish = AsyncMock()
                result = await ai.verify("should fail")

        assert result["passed"] is False
        assert ai._results[0]["status"] == "failed"

    async def test_screenshot_records_path(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)

        mock_ai_ctx = AsyncMock()
        mock_ai_ctx.screenshot.return_value = "/tmp/shot.png"
        mock_ai_ctx._step_started_at = 0

        with patch.object(ai, "_ensure_ai", return_value=mock_ai_ctx):
            path = await ai.screenshot("my_shot")

        assert path == "/tmp/shot.png"
        assert len(ai._screenshots) == 1
        assert ai._screenshots[0]["name"] == "my_shot"
        assert ai._screenshots[0]["path"] == "/tmp/shot.png"

    async def test_multiple_actions_in_sequence(self):
        from skiritai.core.flow import FlowAI

        session = _make_mock_session()
        ai = FlowAI(session=session)

        with patch("skiritai.core.flow.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()

            for i in range(5):
                mock_ai_ctx = AsyncMock()
                mock_ai_ctx.action.return_value = {"success": True, "summary": f"step {i}"}
                mock_ai_ctx.has_replay = MagicMock(return_value=False)
                mock_ai_ctx._step_started_at = 0
                mock_ai_ctx._step_elapsed = 0.1

                with patch.object(ai, "_advance_ai", return_value=mock_ai_ctx):
                    await ai.action(f"step {i}")

        assert len(ai._results) == 5
        step_ids = [r["step_id"] for r in ai._results]
        assert step_ids == ["step_1", "step_2", "step_3", "step_4", "step_5"]


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
