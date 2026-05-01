"""Base class for Python-based test cases."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.engine.ai_context import AIContext
from app.engine.browser import get_launch_args
from app.logger import logger


class BaseCase:
    """Base class for test cases.

    Subclass this and define:
    - setup(): launch browser, navigate to starting URL
    - teardown(): close browser
    - step methods (any async method that takes `ai` as first param)

    Example:
        class MyCase(BaseCase):
            async def setup(self):
                await self.launch_browser()

            async def teardown(self):
                await self.close_browser()

            async def open_page(self, ai):
                await ai.action("打开首页")

            async def search(self, ai):
                await ai.action("搜索关键词")
    """

    def __init__(self, case_dir: Path | None = None):
        self._case_dir = case_dir or Path(inspect.getfile(self.__class__)).parent
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._results: list[dict] = []

    @property
    def case_dir(self) -> Path:
        return self._case_dir

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not launched. Call setup() first.")
        return self._page

    @property
    def results(self) -> list[dict]:
        return self._results

    async def launch_browser(self):
        """Launch browser and create page."""
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(**get_launch_args())
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        logger.info("[Case] Browser launched")

    async def close_browser(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        logger.info("[Case] Browser closed")

    async def setup(self):
        """Override to customize setup. Default launches browser."""
        await self.launch_browser()

    async def teardown(self):
        """Override to customize teardown. Default closes browser."""
        await self.close_browser()

    def get_step_methods(self) -> list[str]:
        """Get list of step method names (methods that take 'ai' as second param after self)."""
        steps = []
        for name in dir(self):
            if name.startswith("_"):
                continue
            attr = getattr(self.__class__, name, None)
            if not callable(attr):
                continue
            # Skip base class methods
            if name in ("close_browser", "get_step_methods", "launch_browser", "run", "run_step", "setup", "teardown"):
                continue
            try:
                sig = inspect.signature(attr)
                params = list(sig.parameters.keys())
                # Check if second param (after self) is 'ai'
                if len(params) >= 2 and params[1] == "ai":
                    steps.append(name)
            except (ValueError, TypeError):
                pass
        return steps

    def _make_ai(self, step_id: str, on_log=None) -> AIContext:
        """Create AIContext for a step."""
        return AIContext(
            page=self.page,
            case_dir=self._case_dir,
            step_id=step_id,
            on_log=on_log,
        )

    async def run_step(self, step_name: str, on_log=None) -> dict:
        """Run a single step method."""
        method = getattr(self, step_name)
        ai = self._make_ai(step_name, on_log)

        logger.info(f"[Step] {step_name} (replay={ai.has_replay()})")

        try:
            result = await method(ai)
            # If method returns a dict, use it; otherwise use ai's result
            if result is None:
                result = ai._last_result or {"success": True, "summary": "完成"}
            self._results.append({
                "step_id": step_name,
                "status": "success" if result.get("success") else "failed",
                "mode": "replay" if ai.has_replay() else "explore",
                "summary": result.get("summary", ""),
            })
            return result
        except Exception as e:
            logger.error(f"[Step] {step_name} error: {e}")
            self._results.append({
                "step_id": step_name,
                "status": "failed",
                "mode": "replay" if ai.has_replay() else "explore",
                "summary": str(e),
                "error": str(e),
            })
            return {"success": False, "summary": str(e)}

    async def run(self) -> dict:
        """Run the full case: setup → steps → teardown."""
        logger.info(f"[Case] {self.__class__.__name__}")

        steps = self.get_step_methods()
        logger.info(f"[Case] Steps: {steps}")

        await self.setup()

        success_count = 0
        for step_name in steps:
            result = await self.run_step(step_name)
            if result.get("success"):
                success_count += 1
            else:
                logger.error(f"[Case] Step {step_name} failed, stopping")
                break

        await self.teardown()

        total = len(steps)
        failed = total - success_count
        status = "completed" if failed == 0 else "failed"

        report = {
            "case_name": self.__class__.__name__,
            "status": status,
            "total_steps": total,
            "success_count": success_count,
            "failed_count": failed,
            "steps": self._results,
        }

        logger.info(f"[Case] Done: {status} ({success_count}/{total})")
        return report
