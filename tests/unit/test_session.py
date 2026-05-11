"""Unit tests for _session — BrowserSession lifecycle and save_report."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================
# 1. BrowserSession Tests
# ============================================================

class TestBrowserSession:
    """Test BrowserSession properties and lifecycle (mocked Playwright)."""

    def test_page_raises_before_start(self):
        from skiritai.core._session import BrowserSession

        session = BrowserSession()
        with pytest.raises(RuntimeError, match="Browser not started"):
            _ = session.page

    def test_started_at_default_zero(self):
        from skiritai.core._session import BrowserSession

        session = BrowserSession()
        assert session.started_at == 0.0

    def _setup_mock_pw(self, mock_pw_factory, mock_page=None):
        """Helper: set up the mock chain async_playwright() → .start() → pw."""
        mock_pw_cm = MagicMock()
        mock_pw = AsyncMock()
        mock_pw_cm.start = AsyncMock(return_value=mock_pw)
        mock_pw_factory.return_value = mock_pw_cm

        mock_browser = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        mock_context = AsyncMock()
        mock_browser.new_context.return_value = mock_context

        page = mock_page or MagicMock()
        mock_context.new_page.return_value = page

        return mock_pw, mock_browser, page

    @patch("skiritai.core._session.async_playwright")
    async def test_start_sets_page(self, mock_pw_factory):
        from skiritai.core._session import BrowserSession

        mock_pw, mock_browser, mock_page = self._setup_mock_pw(mock_pw_factory)

        session = BrowserSession(headless=True)
        await session.start()

        assert session.page is mock_page
        assert session.started_at > 0

        await session.stop()

    @patch("skiritai.core._session.async_playwright")
    async def test_stop_clears_all(self, mock_pw_factory):
        from skiritai.core._session import BrowserSession

        mock_pw, _, _ = self._setup_mock_pw(mock_pw_factory)

        session = BrowserSession()
        await session.start()
        assert session.page is not None

        await session.stop()

        # After stop, page should raise
        with pytest.raises(RuntimeError, match="Browser not started"):
            _ = session.page

    @patch("skiritai.core._session.async_playwright")
    async def test_start_stop_idempotent(self, mock_pw_factory):
        from skiritai.core._session import BrowserSession

        self._setup_mock_pw(mock_pw_factory)

        session = BrowserSession()
        await session.start()
        await session.stop()
        # Double stop should not raise
        await session.stop()

    @patch("skiritai.core._session.async_playwright")
    async def test_context_manager(self, mock_pw_factory):
        from skiritai.core._session import BrowserSession

        self._setup_mock_pw(mock_pw_factory)

        async with BrowserSession() as session:
            assert session.page is not None

        # After context manager exits, page should raise
        with pytest.raises(RuntimeError, match="Browser not started"):
            _ = session.page

    @patch("skiritai.core._session.async_playwright")
    async def test_headless_passed_to_launch(self, mock_pw_factory):
        from skiritai.core._session import BrowserSession

        mock_pw, mock_browser, _ = self._setup_mock_pw(mock_pw_factory)

        session = BrowserSession(headless=True)
        await session.start()

        # Verify launch was called with headless args
        mock_pw.chromium.launch.assert_called_once()
        call_kwargs = mock_pw.chromium.launch.call_args[1]
        assert call_kwargs.get("headless") is True

        await session.stop()

    @patch("skiritai.core._session.async_playwright")
    async def test_stop_calls_browser_close_and_pw_stop(self, mock_pw_factory):
        from skiritai.core._session import BrowserSession

        mock_pw, mock_browser, _ = self._setup_mock_pw(mock_pw_factory)

        session = BrowserSession()
        await session.start()
        await session.stop()

        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()


# ============================================================
# 2. save_report Tests
# ============================================================

class TestSaveReport:
    """Test save_report() file creation and format."""

    def test_creates_report_json(self, tmp_path: Path):
        from skiritai.core._session import save_report

        report = {"case_name": "test", "status": "completed", "steps": []}
        result_dir = save_report(report, tmp_path)

        assert result_dir.exists()
        assert (result_dir / "report.json").exists()

        content = json.loads((result_dir / "report.json").read_text(encoding="utf-8"))
        assert content["case_name"] == "test"
        assert content["status"] == "completed"

    def test_directory_structure(self, tmp_path: Path):
        from skiritai.core._session import save_report

        report = {"case_name": "test", "status": "completed"}
        result_dir = save_report(report, tmp_path)

        # Should create test_results/<timestamp>/report.json
        assert result_dir.parent.name == "test_results"
        # Timestamp dir name format: YYYYMMDD_HHMMSS
        ts_name = result_dir.name
        assert len(ts_name) == 15  # 20240101_120000
        assert "_" in ts_name

    def test_preserves_unicode(self, tmp_path: Path):
        from skiritai.core._session import save_report

        report = {"case_name": "百度搜索测试", "status": "completed"}
        result_dir = save_report(report, tmp_path)

        content = (result_dir / "report.json").read_text(encoding="utf-8")
        assert "百度搜索测试" in content
        # ensure_ascii=False means Chinese chars are NOT escaped
        assert "\\u" not in content

    def test_creates_parent_dirs(self, tmp_path: Path):
        from skiritai.core._session import save_report

        # Use a nested base dir that doesn't exist yet
        nested = tmp_path / "deep" / "nested"
        report = {"case_name": "test"}
        result_dir = save_report(report, nested)
        assert result_dir.exists()

    def test_report_json_is_indented(self, tmp_path: Path):
        from skiritai.core._session import save_report

        report = {"case_name": "test"}
        result_dir = save_report(report, tmp_path)

        content = (result_dir / "report.json").read_text(encoding="utf-8")
        # Indented JSON has newlines and spaces
        assert "\n" in content
        assert '  "' in content

    def test_returns_path(self, tmp_path: Path):
        from skiritai.core._session import save_report

        report = {"case_name": "test"}
        result_dir = save_report(report, tmp_path)
        assert isinstance(result_dir, Path)
        assert result_dir.is_dir()


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
