"""Base class for Python-based test cases."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.engine.ai_context import AIContext, ActionMode
from app.engine.browser import (
    connect_to_browser,
    get_launch_args,
    has_persistent_session,
    is_browser_alive,
    kill_browser,
    launch_browser_server,
    cleanup_session,
)
from app.engine.event_bus import Event, event_bus
from app.logger import logger

# Decorator to set default mode on a step method
def step_mode(mode: ActionMode):
    """Decorator to set the default execution mode for a step method.

    Usage:
        @step_mode("explore")
        async def my_step(self, ai):
            await ai.action("do something")
    """
    def decorator(func):
        func._step_mode = mode
        return func
    return decorator


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

            @step_mode("explore")
            async def search(self, ai):
                await ai.action("搜索关键词")
    """

    def __init__(self, case_dir: Path | None = None, execution_id: str | None = None, results_dir: Path | None = None):
        self._case_dir = case_dir or Path(inspect.getfile(self.__class__)).parent
        self._execution_id = execution_id or "default"
        self._results_dir = results_dir
        self._results: list[dict] = []
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._cdp_port: int | None = None  # Only set in persistent mode

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

    async def launch_browser_persistent(self):
        """Launch browser as an independent process with CDP for session persistence.

        The browser runs as a separate subprocess — it survives when this
        Python program exits. The CDP port is persisted to case_dir.
        """
        self._pw = await async_playwright().start()
        self._cdp_port, self._browser, self._context, self._page = (
            await launch_browser_server(self._pw, self._case_dir)
        )
        logger.info(f"[Case] Persistent browser launched on CDP port {self._cdp_port}")

    async def disconnect_browser(self):
        """Disconnect from browser WITHOUT killing the browser process.

        The browser keeps running. A future process can reconnect via
        the persisted WebSocket endpoint file.
        """
        if self._browser:
            await self._browser.close()  # disconnect, not terminate
            self._browser = None
            self._context = None
            self._page = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        logger.info("[Case] Disconnected from browser (still running)")

    async def reconnect_browser(self):
        """Reconnect to an existing browser via persisted endpoint.

        Raises FileNotFoundError if no session exists, ConnectionError
        if the browser is no longer reachable.
        """
        self._pw = await async_playwright().start()
        self._browser, self._context, self._page = await connect_to_browser(
            self._pw, self._case_dir
        )
        logger.info("[Case] Reconnected to existing browser")

    async def terminate_browser(self):
        """Fully terminate the persistent browser and clean up session file.

        This kills the browser subprocess and removes the session file.
        """
        if self._pw:
            await self._pw.stop()
            self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._cdp_port = None
        kill_browser(self._case_dir)
        logger.info("[Case] Browser terminated and session cleaned up")

    def has_browser_session(self) -> bool:
        """Check if a persistent browser session file exists."""
        return has_persistent_session(self._case_dir)

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
                logger.debug(f"[BaseCase] Cannot inspect signature for method: {name}")
        return steps

    def _make_ai(self, step_id: str, on_log=None) -> AIContext:
        """Create AIContext for a step, reading mode from @step_mode decorator."""
        method = getattr(self.__class__, step_id, None)
        default_mode = getattr(method, "_step_mode", "auto") if method else "auto"
        return AIContext(
            page=self.page,
            case_dir=self._case_dir,
            step_id=step_id,
            on_log=on_log,
            default_mode=default_mode,
            execution_id=self._execution_id,
        )

    async def run_step(self, step_name: str, on_log=None) -> dict:
        """Run a single step method."""
        method = getattr(self, step_name)
        ai = self._make_ai(step_name, on_log)

        logger.info(f"[Step] {step_name} (replay={ai.has_replay()})")

        await event_bus.publish(Event(
            type="step_started",
            execution_id=self._execution_id,
            data={"step_id": step_name},
        ))

        try:
            result = await method(ai)
            # If method returns a dict, use it; otherwise use ai's result
            if result is None:
                result = ai._last_result or {"success": True, "summary": "完成"}
            status = "success" if result.get("success") else "failed"
            self._results.append({
                "step_id": step_name,
                "status": status,
                "mode": "replay" if ai.has_replay() else "explore",
                "summary": result.get("summary", ""),
            })
            await event_bus.publish(Event(
                type="step_completed" if status == "success" else "step_failed",
                execution_id=self._execution_id,
                data={
                    "step_id": step_name,
                    "mode": "replay" if ai.has_replay() else "explore",
                    "summary": result.get("summary", ""),
                },
            ))
            return result
        except Exception as e:
            logger.error(f"[Step] {step_name} error: {e}")
            # Auto screenshot on failure
            if self._results_dir and self._page:
                try:
                    screenshots_dir = self._results_dir / "screenshots"
                    screenshots_dir.mkdir(parents=True, exist_ok=True)
                    screenshot_path = screenshots_dir / f"{step_name}.png"
                    await self._page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"[Step] Screenshot saved: {screenshot_path}")
                except Exception as se:
                    logger.warning(f"[Step] Failed to capture screenshot: {se}")
            self._results.append({
                "step_id": step_name,
                "status": "failed",
                "mode": "replay" if ai.has_replay() else "explore",
                "summary": str(e),
                "error": str(e),
            })
            await event_bus.publish(Event(
                type="step_failed",
                execution_id=self._execution_id,
                data={"step_id": step_name, "error": str(e)},
            ))
            return {"success": False, "summary": str(e)}

    async def run(self) -> dict:
        """Run the full case: setup → steps → teardown."""
        logger.info(f"[Case] {self.__class__.__name__}")

        steps = self.get_step_methods()
        logger.info(f"[Case] Steps: {steps}")

        await event_bus.publish(Event(
            type="execution_started",
            execution_id=self._execution_id,
            data={"case_name": self.__class__.__name__},
        ))

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

        await event_bus.publish(Event(
            type="execution_completed",
            execution_id=self._execution_id,
            data={"report": report},
        ))

        return report
