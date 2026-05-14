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

from skiritai.core._session import BrowserSession, OnLogCallback, save_report
from skiritai.core.ai_context import AIContext, ActionMode
from skiritai.core.case_context import CaseContext
from skiritai.core.notify import notify_if_configured
from skiritai.events import Event, event_bus
from skiritai.logger import logger


class FlowAI:
    """Standalone AI context that manages its own browser lifecycle.

    Created by :func:`flow`.  Do not instantiate directly.

    A single ``AIContext`` is reused across steps so that pre-loaded
    perception data (``analyze_page``, ``get_page_info``) carries over
    to subsequent ``action()`` calls within the same flow session.
    """

    def __init__(
        self,
        session: BrowserSession,
        results_dir: Path | None = None,
        max_steps: int = 20,
        on_log: OnLogCallback = None,
        llm=None,
    ):
        self._session = session
        self._results_dir = results_dir
        self._max_steps = max_steps
        self._on_log = on_log
        self._llm = llm
        self._ctx = CaseContext(case_dir=results_dir or Path("."), execution_id="flow")
        self._step_counter = 0
        self._results: list[dict] = []
        self._screenshots: list[dict] = []
        # Reused AIContext — preserves analyze_page / get_page_info cache
        self._ai: AIContext | None = None

    def _next_step_id(self, prefix: str = "") -> str:
        self._step_counter += 1
        return f"{prefix}{self._step_counter}" if prefix else f"step_{self._step_counter}"

    def _ensure_ai(self, step_id: str) -> AIContext:
        """Get or create the persistent AIContext for this session.

        If one already exists and has a matching step_id, reuse it (preserving
        cached perception data).  Otherwise create a fresh one.
        """
        if self._ai is not None and self._ai.step_id == step_id:
            return self._ai
        self._ai = AIContext(
            page=self._session.page,
            case_dir=self._results_dir or Path("."),
            step_id=step_id,
            on_log=self._on_log,
            default_mode="auto",
            execution_id="flow",
            max_steps=self._max_steps,
            llm=self._llm,
        )
        return self._ai

    def _advance_ai(self, step_id: str) -> AIContext:
        """Create a new AIContext for a new step, carrying over perception cache."""
        if self._ai is not None:
            ai = self._ai.copy_for_step(step_id)
        else:
            ai = AIContext(
                page=self._session.page,
                case_dir=self._results_dir or Path("."),
                step_id=step_id,
                on_log=self._on_log,
                default_mode="auto",
                execution_id="flow",
                max_steps=self._max_steps,
                llm=self._llm,
            )
        self._ai = ai
        return ai

    # ---- Public API ----

    async def action(self, description: str, mode: ActionMode | None = None) -> dict:
        """Execute a natural-language action via the AI agent.

        Args:
            description: What to do, in plain language.
            mode: Execution mode override ("auto", "explore", "replay").

        Returns:
            Result dict with keys: success, summary, steps.
        """
        step_id = self._next_step_id()
        ai = self._advance_ai(step_id)
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
            "title": description if len(description) <= 50 else description[:47] + "...",
            "status": "success" if result.get("success") else "failed",
            "mode": result.get("mode", "explore"),
            "summary": result.get("summary", ""),
            "elapsed": round(ai._step_elapsed, 2),
            "type": "action",
            "screenshots": [{"name": s["name"], "path": s["path"], "step_id": step_id}
                            for s in ai._screenshots],
        }
        self._results.append(entry)
        self._screenshots.extend(entry["screenshots"])

        status = "success" if result.get("success") else "failed"
        await event_bus.publish(Event(
            type="step_completed" if status == "success" else "step_failed",
            execution_id="flow",
            data={"step_id": step_id, "summary": result.get("summary", "")},
        ))

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
        step_id = self._next_step_id()
        ai = self._advance_ai(step_id)
        self._ctx.current_step = step_id
        ai._step_started_at = time.time()

        result = await ai.verify(assertion, take_screenshot=take_screenshot)
        ai._step_elapsed = time.time() - ai._step_started_at

        # Track failure screenshot
        screenshots = []
        if not result.get("passed") and result.get("screenshot"):
            ss_info = {"name": f"verify_fail_{step_id}", "path": result["screenshot"], "step_id": step_id}
            screenshots.append(ss_info)
            self._screenshots.append(ss_info)

        display_name = assertion if len(assertion) <= 40 else assertion[:37] + "..."
        entry = {
            "step_id": display_name,
            "title": assertion,
            "status": "passed" if result.get("passed") else "failed",
            "type": "verify",
            "mode": "verify",
            "assertion": assertion,
            "reason": result.get("reason", ""),
            "elapsed": round(ai._step_elapsed, 2),
            "screenshots": screenshots,
        }
        self._results.append(entry)
        self._ctx.current_step = None
        return result

    async def screenshot(self, name: str = "screenshot") -> str:
        """Capture a full-page screenshot.

        Args:
            name: Descriptive name for the screenshot file.

        Returns:
            File path of the saved screenshot.
        """
        step_id = self._next_step_id()
        ai = self._ensure_ai(step_id)
        ai._step_started_at = time.time()
        path = await ai.screenshot(name)
        elapsed = time.time() - ai._step_started_at

        ss_info = {"name": name, "path": path, "step_id": step_id, "timestamp": ai._step_started_at}
        self._screenshots.append(ss_info)

        entry = {
            "step_id": name,
            "title": f"Screenshot: {name}",
            "status": "success",
            "type": "screenshot",
            "mode": "screenshot",
            "summary": f"Screenshot: {name}",
            "elapsed": round(elapsed, 2),
            "screenshots": [ss_info],
        }
        self._results.append(entry)
        return path

    async def analyze_page(self) -> dict:
        """Analyze page DOM and return structured data.

        The result is cached and automatically injected into subsequent
        ``action()`` calls in this flow session.
        """
        step_id = self._next_step_id("analyze_")
        ai = self._ensure_ai(step_id)
        return await ai.analyze_page()

    async def get_page_info(self) -> str:
        """Get page title, URL, and text summary.

        The result is cached and automatically injected into subsequent
        ``action()`` calls in this flow session.
        """
        step_id = self._next_step_id("info_")
        ai = self._ensure_ai(step_id)
        return await ai.get_page_info()

    # ---- Report ----

    def _save_report(self) -> None:
        if not self._results_dir or not self._results:
            return

        from skiritai.core.report_builder import normalize_report

        raw = {
            "case_name": "flow",
            "status": "completed" if all(r["status"] in ("success", "passed") for r in self._results) else "failed",
            "source": "flow",
            "total_steps": len(self._results),
            "success_count": sum(1 for r in self._results if r["status"] in ("success", "passed")),
            "failed_count": sum(1 for r in self._results if r["status"] == "failed"),
            "steps": self._results,
            "elapsed_seconds": round(time.time() - self._session.started_at, 2),
        }
        report = normalize_report(raw)
        save_report(report, self._results_dir, label="Flow")

        # Fire-and-forget notification (non-blocking, best-effort)
        notify_if_configured(report)


@asynccontextmanager
async def flow(
    headless: bool | None = None,
    results_dir: Path | str | None = None,
    max_steps: int = 20,
    on_log: OnLogCallback = None,
    llm=None,
):
    """Functional test context — no subclass needed.

    Launches a browser and provides an ``ai`` object with
    ``action``, ``verify``, ``screenshot``, ``analyze_page``, and ``get_page_info``.

    Args:
        headless: Run browser in headless mode. ``None`` = read from env.
        results_dir: Directory to save results and reports.
        max_steps: Maximum agent tool-call steps per action.
        on_log: Optional callback for real-time log streaming.
        llm: Optional LLM provider instance.  If ``None``, auto-detects from env.

    Yields:
        :class:`FlowAI` instance.

    Example::

        from skiritai import flow

        async with flow() as ai:
            await ai.action("打开百度首页 https://www.baidu.com")
            await ai.screenshot("homepage")
            await ai.verify("页面标题包含'百度'")

    With explicit LLM::

        from skiritai import flow
        from skiritai.llm import OpenAIProvider

        async with flow(llm=OpenAIProvider(api_key="sk-xxx", model="gpt-5")) as ai:
            await ai.action("打开百度首页")
    """
    from skiritai.core.agent_loop import register_all_tools
    register_all_tools()

    rd = Path(results_dir) if results_dir else None
    session = BrowserSession(headless=headless)
    await session.start()
    logger.info("[Flow] Browser launched")
    runner = FlowAI(session=session, results_dir=rd, max_steps=max_steps, on_log=on_log, llm=llm)
    try:
        yield runner
    finally:
        runner._save_report()
        await session.stop()
        logger.info("[Flow] Browser closed")
