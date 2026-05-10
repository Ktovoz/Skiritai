"""E2E tests — browser session persistence via CDP (disconnect & reconnect)."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

os.environ["SKIRITAI_HEADLESS"] = "true"

from playwright.async_api import async_playwright

from skiritai.core.ai_context import AIContext
from skiritai.core.base_case import BaseCase
from skiritai.core.browser import is_browser_alive


class TestBrowserSessionPersistence:
    """Test browser session persistence via CDP."""

    @pytest.mark.asyncio
    async def test_launch_persistent_browser(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_persist_")
        case_dir = Path(tmpdir) / "persist_case"
        case_dir.mkdir()

        try:
            case = BaseCase(case_dir=case_dir)
            await case.launch_browser_persistent()

            try:
                assert case._page is not None
                assert case._browser is not None
                assert case._cdp_port is not None

                assert case.has_browser_session() is True
                assert is_browser_alive(case_dir) is True

                await case._page.goto(url)
                await case._page.wait_for_load_state("networkidle")
                title = await case._page.title()
                assert "E2E Test Page" in title
            finally:
                await case.terminate_browser()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_reconnect_and_continue_step(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_reconnect_")
        case_dir = Path(tmpdir) / "reconnect_case"
        case_dir.mkdir()

        try:
            case1 = BaseCase(case_dir=case_dir, execution_id="phase1")
            await case1.launch_browser_persistent()

            await case1._page.goto(url)
            await case1._page.wait_for_load_state("networkidle")
            await case1._page.fill("#text-input", "Step 1 Value")

            val = await case1._page.input_value("#text-input")
            assert val == "Step 1 Value"

            await case1.disconnect_browser()
            assert case1._page is None
            assert case1.has_browser_session() is True

            await asyncio.sleep(0.5)

            case2 = BaseCase(case_dir=case_dir, execution_id="phase2")
            await case2.reconnect_browser()

            persisted_val = await case2._page.input_value("#text-input")
            assert persisted_val == "Step 1 Value"

            assert url in case2._page.url

            await case2._page.click("#submit-btn")
            result_text = await case2._page.text_content("#result")
            assert "Step 1 Value" in result_text

            await case2.terminate_browser()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_replay_scripts_across_reconnect(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_replay_reconnect_")
        case_dir = Path(tmpdir) / "replay_case"
        case_dir.mkdir()
        scripts_dir = case_dir / "scripts"
        scripts_dir.mkdir()

        (scripts_dir / "fill_input.py").write_text(
            "async def run(page, context):\n"
            '    await page.fill("#text-input", "Replay Persist")\n',
            encoding="utf-8",
        )
        (scripts_dir / "click_submit.py").write_text(
            "async def run(page, context):\n"
            '    await page.click("#submit-btn")\n',
            encoding="utf-8",
        )

        try:
            case1 = BaseCase(case_dir=case_dir)
            await case1.launch_browser_persistent()
            await case1._page.goto(url)
            await case1._page.wait_for_load_state("networkidle")

            ai1 = AIContext(page=case1._page, case_dir=case_dir, step_id="fill_input")
            result1 = await ai1.action("fill input", mode="replay")
            assert result1["success"] is True

            await case1.disconnect_browser()
            await asyncio.sleep(0.5)

            case2 = BaseCase(case_dir=case_dir)
            await case2.reconnect_browser()

            val = await case2._page.input_value("#text-input")
            assert val == "Replay Persist"

            ai2 = AIContext(page=case2._page, case_dir=case_dir, step_id="click_submit")
            result2 = await ai2.action("click submit", mode="replay")
            assert result2["success"] is True

            result_text = await case2._page.text_content("#result")
            assert "Replay Persist" in result_text

            await case2.terminate_browser()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_cleanup_terminates_browser(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_terminate_")
        case_dir = Path(tmpdir) / "terminate_case"
        case_dir.mkdir()

        try:
            case = BaseCase(case_dir=case_dir)
            await case.launch_browser_persistent()

            assert case.has_browser_session() is True

            await case.terminate_browser()

            assert case.has_browser_session() is False
            assert case._page is None
            assert case._browser is None
            assert case._cdp_port is None
            assert case._pw is None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_session_status_detection(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_detect_")
        case_dir = Path(tmpdir) / "detect_case"
        case_dir.mkdir()

        try:
            case = BaseCase(case_dir=case_dir)

            assert case.has_browser_session() is False
            assert is_browser_alive(case_dir) is False

            await case.launch_browser_persistent()
            assert case.has_browser_session() is True
            assert is_browser_alive(case_dir) is True

            await case.disconnect_browser()
            assert case.has_browser_session() is True
            assert is_browser_alive(case_dir) is True

            case2 = BaseCase(case_dir=case_dir)
            assert case2.has_browser_session() is True

            await case2.terminate_browser()
            assert case2.has_browser_session() is False
            assert is_browser_alive(case_dir) is False
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_cross_process_reconnection(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_cross_")
        case_dir = Path(tmpdir) / "cross_case"
        case_dir.mkdir()

        try:
            case_p1 = BaseCase(case_dir=case_dir, execution_id="process_1")
            await case_p1.launch_browser_persistent()
            await case_p1._page.goto(url)
            await case_p1._page.wait_for_load_state("networkidle")
            await case_p1._page.fill("#text-input", "From Process 1")

            await case_p1.disconnect_browser()

            case_p2 = BaseCase(case_dir=case_dir, execution_id="process_2")

            assert case_p2.has_browser_session() is True

            await case_p2.reconnect_browser()

            val = await case_p2._page.input_value("#text-input")
            assert val == "From Process 1"

            await case_p2._page.click("#submit-btn")
            result = await case_p2._page.text_content("#result")
            assert "From Process 1" in result

            await case_p2.terminate_browser()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
        env={**os.environ, "HEADLESS": "true"},
    )
    sys.exit(result.returncode)
