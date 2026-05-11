"""Flow API — functional, no-subclass test runner.

Usage::

    from skiritai import flow

    async def main():
        async with flow() as ai:
            await ai.action("打开百度首页 https://www.baidu.com")
            await ai.action("搜索关键词 Playwright")
            await ai.screenshot("result")
            await ai.verify("搜索结果包含 Playwright 相关内容")

    import asyncio
    asyncio.run(main())

Supports headless mode and custom results directory::

    async with flow(headless=True, results_dir=Path("results")) as ai:
        ...
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from skiritai.core.ai_context import AIContext, ActionMode
from skiritai.core.browser import get_launch_args
from skiritai.core.case_context import CaseContext
from skiritai.events import Event, event_bus
from skiritai.logger import logger


class FlowAI:
    """Standalone AI context that manages its own browser lifecycle.

    Created by :func:`flow`.  Do not instantiate directly.
    """

    def __init__(
        self,
        headless: bool | None = None,
        results_dir: Path | None = None,
        max_steps: int = 20,
    ):
        self._headless = headless
        self._results_dir = results_dir
        self._max_steps = max_steps
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._ai: AIContext | None = None
        self._ctx = CaseContext(case_dir=results_dir or Path("."), execution_id="flow")
        self._step_counter = 0
        self._results: list[dict] = []
        self._screenshots: list[dict] = []
        self._started_at: float = 0.0

    async def _start(self) -> None:
        """Launch browser — called when entering the context manager."""
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(**get_launch_args(self._headless))
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        self._ctx.browser.mode = "standard"
        self._ctx.browser.started_at = time.time()
        self._started_at = time.time()
        logger.info("[Flow] Browser launched")

    async def _stop(self) -> None:
        """Close browser — called when exiting the context manager."""
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._ctx.browser.mode = ""
        logger.info("[Flow] Browser closed")

        # Save report if results_dir is set
        if self._results_dir and self._results:
            self._save_report()

    def _next_step_id(self, prefix: str = "") -> str:
        self._step_counter += 1
        return f"{prefix}{self._step_counter}" if prefix else f"step_{self._step_counter}"

    def _make_ai(self, step_id: str) -> AIContext:
        return AIContext(
            page=self._page,
            case_dir=self._results_dir or Path("."),
            step_id=step_id,
            default_mode="auto",
            execution_id="flow",
            max_steps=self._max_steps,
        )

    # ---- Public API (mirrors AIContext) ----

    async def action(self, description: str, mode: ActionMode | None = None) -> dict:
        """Execute a natural-language action via the AI agent.

        Args:
            description: What to do, in plain language.
            mode: Execution mode override ("auto", "explore", "replay").

        Returns:
            Result dict with keys: success, summary, steps.
        """
        step_id = self._next_step_id()
        ai = self._make_ai(step_id)
        self._ai = ai
        self._ctx.current_step = step_id
        ai._step_started_at = time.time()

        await event_bus.publish(Event(
            type="step_started",
            execution_id="flow",
            data={"step_id": step_id, "type": "action"},
        ))

        result = await ai.action(description, mode=mode)
        ai._step_elapsed = time.time() - ai._step_started_at

        entry = {
            "step_id": step_id,
            "status": "success" if result.get("success") else "failed",
            "mode": "replay" if ai.has_replay() else "explore",
            "summary": result.get("summary", ""),
            "elapsed": round(ai._step_elapsed, 2),
            "type": "action",
        }
        self._results.append(entry)

        status = "success" if result.get("success") else "failed"
        await event_bus.publish(Event(
            type="step_completed" if status == "success" else "step_failed",
            execution_id="flow",
            data={"step_id": step_id, "summary": result.get("summary", "")},
        ))

        self._ai = None
        self._ctx.current_step = None
        return result

    async def verify(self, assertion: str, take_screenshot: bool = True) -> dict:
        """Run an AI-powered assertion (non-blocking on failure).

        Args:
            assertion: Natural language assertion.
            take_screenshot: Capture screenshot on failure.

        Returns:
            dict with keys: passed, reason, screenshot.
        """
        step_id = self._next_step_id("verify_")
        ai = self._make_ai(step_id)
        self._ai = ai
        self._ctx.current_step = step_id
        ai._step_started_at = time.time()

        result = await ai.verify(assertion, take_screenshot=take_screenshot)
        ai._step_elapsed = time.time() - ai._step_started_at

        entry = {
            "step_id": step_id,
            "status": "passed" if result.get("passed") else "failed",
            "type": "verify",
            "assertion": assertion,
            "reason": result.get("reason", ""),
            "elapsed": round(ai._step_elapsed, 2),
        }
        self._results.append(entry)
        self._ai = None
        self._ctx.current_step = None
        return result

    async def screenshot(self, name: str = "screenshot") -> str:
        """Capture a full-page screenshot.

        Args:
            name: Descriptive name for the screenshot file.

        Returns:
            File path of the saved screenshot.
        """
        step_id = self._next_step_id("ss_")
        ai = self._make_ai(step_id)
        ai._step_started_at = time.time()
        path = await ai.screenshot(name)
        self._screenshots.append({"name": name, "path": path})
        return path

    async def analyze_page(self) -> dict:
        """Analyze page DOM and return structured data."""
        step_id = self._next_step_id("analyze_")
        ai = self._make_ai(step_id)
        return await ai.analyze_page()

    async def get_page_info(self) -> str:
        """Get page title, URL, and text summary."""
        step_id = self._next_step_id("info_")
        ai = self._make_ai(step_id)
        return await ai.get_page_info()

    # ---- Report ----

    def _save_report(self) -> None:
        import json
        from datetime import datetime

        results_dir = self._results_dir
        ts_dir = results_dir / "test_results" / datetime.now().strftime("%Y%m%d_%H%M%S")
        ts_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "case_name": "flow",
            "status": "completed" if all(r["status"] in ("success", "passed") for r in self._results) else "failed",
            "total_steps": len(self._results),
            "success_count": sum(1 for r in self._results if r["status"] in ("success", "passed")),
            "failed_count": sum(1 for r in self._results if r["status"] == "failed"),
            "steps": self._results,
            "elapsed_seconds": round(time.time() - self._started_at, 2),
        }

        (ts_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"[Flow] Report saved to {ts_dir}")


@asynccontextmanager
async def flow(
    headless: bool | None = None,
    results_dir: Path | str | None = None,
    max_steps: int = 20,
):
    """Functional test context — no subclass needed.

    Launches a browser and provides an ``ai`` object with
    ``action``, ``verify``, ``screenshot``, ``analyze_page``, and ``get_page_info``.

    Args:
        headless: Run browser in headless mode. ``None`` = read from env.
        results_dir: Directory to save results and reports.
        max_steps: Maximum agent tool-call steps per action.

    Yields:
        :class:`FlowAI` instance.

    Example::

        from skiritai import flow

        async with flow() as ai:
            await ai.action("打开百度首页 https://www.baidu.com")
            await ai.screenshot("homepage")
            await ai.verify("页面标题包含'百度'")
    """
    from skiritai.core.agent_loop import register_all_tools
    register_all_tools()

    rd = Path(results_dir) if results_dir else None
    runner = FlowAI(headless=headless, results_dir=rd, max_steps=max_steps)
    await runner._start()
    try:
        yield runner
    finally:
        await runner._stop()
