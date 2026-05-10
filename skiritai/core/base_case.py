"""Base class for Python-based test cases."""
from __future__ import annotations

import inspect
import time
from enum import Enum
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from skiritai.core.ai_context import AIContext, ActionMode
from skiritai.core.browser import (
    connect_to_browser,
    get_launch_args,
    has_persistent_session,
    kill_browser,
    launch_browser_server,
)
from skiritai.core.case_context import CaseContext
from skiritai.events import Event, event_bus
from skiritai.logger import logger


# ---------------------------------------------------------------------------
# Failure policy — controls what happens when a step fails
# ---------------------------------------------------------------------------

class FailurePolicy(str, Enum):
    """What to do when a step fails in the run loop."""
    ABORT = "abort"  # Stop execution (default, backward compatible)
    SKIP = "skip"  # Skip this step and continue to the next
    RETRY = "retry"  # Retry the step up to N times, then abort


class StepResult:
    """Structured result returned from hook methods to control execution flow."""

    def __init__(
            self,
            proceed: bool = True,
            retry: bool = False,
            skip: bool = False,
    ):
        self.proceed = proceed
        self.retry = retry
        self.skip = skip

    @classmethod
    def continue_(cls) -> StepResult:
        return cls(proceed=True)

    @classmethod
    def do_retry(cls) -> StepResult:
        return cls(retry=True, proceed=False)

    @classmethod
    def do_skip(cls) -> StepResult:
        return cls(skip=True, proceed=True)


def step(func):
    """Decorator to explicitly mark a method as a test step (OPTIONAL).

    All public methods are auto-detected as steps, so @step is purely
    for documentation / explicitness.

    Usage (old style, still supported):
        @step
        async def my_step(self, ai):
            await ai.action("do something")

    Preferred new style (no decorator, no ai param):
        async def my_step(self):
            await self.ai.action("do something")
    """
    func._is_step = True
    return func


def step_mode(mode: ActionMode):
    """Decorator to set the default execution mode for a step method.

    Usage:
        @step_mode("explore")
        async def my_step(self, ai):
            await ai.action("do something")
    """

    def decorator(func):
        func._step_mode = mode
        func._is_step = True
        return func

    return decorator


def on_failure(policy: FailurePolicy, max_retries: int = 1):
    """Decorator to set the failure policy for a step.

    Usage:
        @on_failure(FailurePolicy.RETRY, max_retries=2)
        async def my_step(self, ai):
            await ai.action("do something")

        @on_failure(FailurePolicy.SKIP)
        async def optional_step(self, ai):
            await ai.action("do something optional")
    """

    def decorator(func):
        func._failure_policy = policy
        func._max_retries = max_retries
        func._is_step = True
        return func

    return decorator


def max_steps(limit: int):
    """Decorator to set the maximum agent steps (recursion_limit) for a step.

    Usage:
        @max_steps(30)
        async def complex_step(self):
            await self.ai.action("do something that needs many tool calls")
    """

    def decorator(func):
        func._max_steps = limit
        func._is_step = True
        return func

    return decorator


class BaseCase:
    """Base class for test cases.

    Subclass this and define:
    - setup(): launch browser, navigate to starting URL
    - teardown(): close browser
    - step methods: any async method with no required params (uses self.ai)

    Optional hooks to override:
    - before_step(step_name): called before each step
    - after_step(step_name, result): called after each step (success or failure)
    - on_step_error(step_name, error): called when a step raises an exception

    Step methods are auto-detected: all public callable methods except
    lifecycle, hooks, and browser methods are treated as steps.
    No decorator required.

    Use self.ai.action("...") inside steps — no need to declare ``ai`` as a param.
    The old style ``async def step(self, ai)`` is still supported.

    Example:
        class MyCase(BaseCase):
            async def setup(self):
                await self.launch_browser()

            async def teardown(self):
                await self.close_browser()

            async def open_page(self):
                await self.ai.action("打开首页")

            @step_mode("explore")
            async def search(self):
                await self.ai.action("搜索关键词")

            @on_failure(FailurePolicy.SKIP)
            async def optional_check(self):
                await self.ai.action("可选的检查")

            async def before_step(self, step_name: str):
                print(f"About to run: {step_name}")

            async def after_step(self, step_name: str, result: dict):
                print(f"Finished: {step_name} -> {result.get('summary')}")
    """

    # Methods excluded from auto-detection as steps
    _RESERVED_METHODS = frozenset({
        # Lifecycle
        "setup", "teardown",
        # Browser
        "launch_browser", "close_browser",
        "launch_browser_persistent", "disconnect_browser",
        "reconnect_browser", "terminate_browser",
        "has_browser_session",
        # Hooks
        "before_step", "after_step", "on_step_error",
        # Runner
        "get_step_methods", "run", "run_step",
    })

    # Default max agent tool-call steps per step method (LangGraph recursion_limit).
    # Override via class attribute or @max_steps(N) decorator on individual methods.
    max_steps: int = 20

    def __init__(self, case_dir: Path | None = None, execution_id: str | None = None, results_dir: Path | None = None):
        self._case_dir = case_dir or Path(inspect.getfile(self.__class__)).parent
        self._execution_id = execution_id or "default"
        self._results_dir = results_dir
        self._results: list[dict] = []
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._ai: AIContext | None = None

        # Per-case headless override: None = use env var, True/False = explicit
        self.headless: bool | None = None

        # Global context — state machine + store + browser session info
        self._ctx = CaseContext(
            case_dir=self._case_dir,
            execution_id=self._execution_id,
        )

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

    @property
    def ctx(self) -> CaseContext:
        """Access the global case context (state machine, store, browser info)."""
        return self._ctx

    @property
    def ai(self) -> AIContext:
        """AI action context — available inside step methods.

        Use self.ai.action("...") to describe operations in natural language.
        """
        if self._ai is None:
            raise RuntimeError("self.ai is only available inside a step method")
        return self._ai

    @property
    def _cdp_port(self):
        """CDP port of the persistent browser (None when not in persistent mode)."""
        return self._ctx.browser.cdp_port

    # ---- Browser lifecycle ----

    async def launch_browser(self):
        """Launch browser and create page.

        Uses self.headless if set (True/False), otherwise reads env vars.
        Set self.headless = True in __init__ or as a class attribute to
        control per-case:
            class MyCase(BaseCase):
                headless = True  # this case always runs headless
        """
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(**get_launch_args(self.headless))
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        # Update context
        self._ctx.browser.mode = "standard"
        self._ctx.browser.started_at = time.time()
        logger.info("[Case] Browser launched")

    async def close_browser(self):
        """Close browser and clean up perception layer."""
        await self._cleanup_perception()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._ctx.browser.mode = ""
        self._ctx.browser.cdp_port = None
        logger.info("[Case] Browser closed")

    async def launch_browser_persistent(self):
        """Launch browser as an independent process with CDP for session persistence.

        The browser runs as a separate subprocess — it survives when this
        Python program exits. The CDP port is persisted to case_dir.
        """
        self._pw = await async_playwright().start()
        cdp_port, browser, context, page = (
            await launch_browser_server(self._pw, self._case_dir, self.headless)
        )
        self._browser = browser
        self._context = context
        self._page = page
        # Update context
        self._ctx.browser.mode = "persistent"
        self._ctx.browser.cdp_port = cdp_port
        self._ctx.browser.started_at = time.time()
        # Connect perception layer to the same CDP port
        await self._init_perception()
        logger.info(f"[Case] Persistent browser launched on CDP port {cdp_port}")

    async def disconnect_browser(self):
        """Disconnect from browser WITHOUT killing the browser process."""
        await self._cleanup_perception()
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        logger.info("[Case] Disconnected from browser (still running)")

    async def reconnect_browser(self):
        """Reconnect to an existing browser via persisted endpoint."""
        self._pw = await async_playwright().start()
        self._browser, self._context, self._page = await connect_to_browser(
            self._pw, self._case_dir
        )
        # Restore CDP port from session file
        from skiritai.core.browser import load_session
        session = load_session(self._case_dir)
        if session:
            self._ctx.browser.cdp_port = session.get("cdp_port")
            self._ctx.browser.pid = session.get("pid")
            self._ctx.browser.mode = "persistent"
        # Re-connect perception layer
        await self._init_perception()
        logger.info("[Case] Reconnected to existing browser")

    async def terminate_browser(self):
        """Fully terminate the persistent browser and clean up."""
        await self._cleanup_perception()
        if self._pw:
            await self._pw.stop()
            self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._ctx.browser.cdp_port = None
        self._ctx.browser.pid = None
        self._ctx.browser.mode = ""
        kill_browser(self._case_dir)
        logger.info("[Case] Browser terminated and session cleaned up")

    # ---- Perception layer lifecycle ----

    async def _init_perception(self) -> None:
        """Connect browser-use BrowserSession to the same CDP port for DOM perception.

        Only connects when CDP port is available (persistent mode or explicit config).
        Standard mode falls back to Playwright evaluate gracefully.
        """
        cdp_port = self._ctx.browser.cdp_port
        if not cdp_port:
            logger.debug("[Perception] No CDP port, perception layer unavailable")
            return

        try:
            from skiritai.core.perception import create_browser_session, set_browser_session
            cdp_url = f"http://127.0.0.1:{cdp_port}"
            session = await create_browser_session(cdp_url)
            set_browser_session(session)
            self._ctx.perception_mode = "browser_use"
            logger.info(f"[Perception] Connected to CDP port {cdp_port}")
        except Exception as e:
            logger.warning(f"[Perception] Failed to connect: {e}, falling back to Playwright evaluate")
            self._ctx.perception_mode = "playwright_fallback"

    async def _cleanup_perception(self) -> None:
        """Disconnect the browser-use BrowserSession (does NOT close the browser)."""
        try:
            from skiritai.core.perception import cleanup
            await cleanup()
        except Exception as e:
            logger.debug(f"[Perception] Cleanup error: {e}")
        self._ctx.perception_mode = "playwright_fallback"

    def has_browser_session(self) -> bool:
        """Check if a persistent browser session file exists."""
        return has_persistent_session(self._case_dir)

    # ---- Setup / Teardown ----

    async def setup(self):
        """Override to customize setup. Default launches browser."""
        await self.launch_browser()

    async def teardown(self):
        """Override to customize teardown. Default closes browser."""
        await self.close_browser()

    # ---- Hook methods (override in subclass) ----

    async def before_step(self, step_name: str) -> None:
        """Called before each step executes.

        Override to add custom pre-step logic (e.g., logging, data preparation).
        Raising an exception here will abort the step.
        """
        pass

    async def after_step(self, step_name: str, result: dict) -> None:
        """Called after each step completes (whether success or failure).

        Override to add custom post-step logic (e.g., cleanup, notifications).
        Exceptions here are logged but do not affect execution flow.
        """
        pass

    async def on_step_error(self, step_name: str, error: Exception) -> StepResult:
        """Called when a step raises an exception.

        Override to customize error handling. Return a StepResult to control
        what happens next:
        - StepResult.continue_(): proceed normally (result is marked failed)
        - StepResult.do_retry(): retry this step
        - StepResult.do_skip(): skip this step and continue to the next

        Default behavior: return StepResult.continue_() (mark failed, use policy).
        """
        return StepResult.continue_()

    # ---- Step discovery ----

    def get_step_methods(self) -> list[str]:
        """Auto-detect all public methods as step methods.

        Steps are discovered in definition order (Python 3.7+ __dict__ preserves
        insertion order), so you control execution order by defining methods
        in the sequence they should run.
        """
        steps = []
        # Walk MRO in reverse so base classes come first, subclass overrides last.
        # Within each class, __dict__ preserves definition order (Python 3.7+).
        seen = set()
        for cls in reversed(type(self).__mro__):
            for name, attr in cls.__dict__.items():
                if name.startswith("_"):
                    continue
                if name in self._RESERVED_METHODS:
                    continue
                if name in seen:
                    continue
                if not callable(attr):
                    continue
                if isinstance(attr, property):
                    continue
                seen.add(name)
                steps.append(name)
        return steps

    # ---- Step execution ----

    def _make_ai(self, step_id: str, on_log=None) -> AIContext:
        """Create AIContext for a step, reading decorators and class config."""
        method = getattr(self.__class__, step_id, None)
        default_mode = getattr(method, "_step_mode", "auto") if method else "auto"
        # Resolve max_steps: @max_steps(N) decorator > class attribute > default 20
        step_max_steps = getattr(method, "_max_steps", None) if method else None
        effective_max_steps = step_max_steps if step_max_steps is not None else self.max_steps
        return AIContext(
            page=self.page,
            case_dir=self._case_dir,
            step_id=step_id,
            on_log=on_log,
            default_mode=default_mode,
            execution_id=self._execution_id,
            max_steps=effective_max_steps,
        )

    async def run_step(self, step_name: str, on_log=None) -> dict:
        """Run a single step method with hooks.

        Supports both calling conventions:
            async def step(self):        # new style — use self.ai
            async def step(self, ai):    # old style — ai parameter (backward compat)
        """
        method = getattr(self, step_name)
        ai = self._make_ai(step_name, on_log)
        self._ai = ai  # expose via self.ai property

        # Detect calling convention: does the method expect an 'ai' parameter?
        # Note: method is a bound method, so 'self' is already stripped from the signature.
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        takes_ai_param = len(params) >= 1 and params[0] == "ai"

        self._ctx.current_step = step_name
        logger.info(f"[Step] {step_name} (replay={ai.has_replay()})")

        await event_bus.publish(Event(
            type="step_started",
            execution_id=self._execution_id,
            data={"step_id": step_name},
        ))

        # --- before_step hook ---
        try:
            await self.before_step(step_name)
        except Exception as e:
            logger.error(f"[Hook] before_step({step_name}) raised: {e}")

        ai._step_started_at = time.time()

        try:
            if takes_ai_param:
                result = await method(ai)
            else:
                result = await method()
            if result is None:
                result = ai._last_result or {"success": True, "summary": "完成"}
            status = "success" if result.get("success") else "failed"
            ai._step_elapsed = time.time() - ai._step_started_at

            step_entry = {
                "step_id": step_name,
                "status": status,
                "mode": "replay" if ai.has_replay() else "explore",
                "summary": result.get("summary", ""),
                "elapsed": round(ai._step_elapsed, 2),
                "screenshots": list(ai._screenshots),
                "verifications": list(ai._verifications),
            }
            self._results.append(step_entry)

            if status == "success":
                self._ctx.completed_steps.append(step_name)
            else:
                self._ctx.failed_step = step_name

            await event_bus.publish(Event(
                type="step_completed" if status == "success" else "step_failed",
                execution_id=self._execution_id,
                data={
                    "step_id": step_name,
                    "mode": "replay" if ai.has_replay() else "explore",
                    "summary": result.get("summary", ""),
                    "elapsed": step_entry["elapsed"],
                },
            ))

            # --- after_step hook ---
            try:
                await self.after_step(step_name, result)
            except Exception as hook_exc:
                logger.error(f"[Hook] after_step({step_name}) raised: {hook_exc}")

            return result
        except Exception as e:
            logger.error(f"[Step] {step_name} error: {e}")
            ai._step_elapsed = time.time() - ai._step_started_at

            # --- on_step_error hook ---
            hook_result = StepResult.continue_()
            try:
                hook_result = await self.on_step_error(step_name, e)
            except Exception as hook_exc:
                logger.error(f"[Hook] on_step_error({step_name}) raised: {hook_exc}")

            self._ctx.failed_step = step_name
            # Auto screenshot on failure (base64 for report)
            auto_screenshot = None
            if self._page:
                try:
                    import base64, tempfile
                    path = str(Path(tempfile.gettempdir()) / f"skiritai_error_{step_name}.png")
                    await self._page.screenshot(path=path, full_page=True)
                    auto_screenshot = {"name": f"error_{step_name}", "path": path}
                    logger.info(f"[Step] Error screenshot saved: {path}")
                except Exception as se:
                    logger.warning(f"[Step] Failed to capture screenshot: {se}")

            step_screenshots = list(ai._screenshots)
            if auto_screenshot:
                step_screenshots.append(auto_screenshot)

            result = {"success": False, "summary": str(e), "_hook_result": hook_result}
            self._results.append({
                "step_id": step_name,
                "status": "failed",
                "mode": "replay" if ai.has_replay() else "explore",
                "summary": str(e),
                "error": str(e),
                "elapsed": round(ai._step_elapsed, 2),
                "screenshots": step_screenshots,
                "verifications": list(ai._verifications),
            })
            await event_bus.publish(Event(
                type="step_failed",
                execution_id=self._execution_id,
                data={"step_id": step_name, "error": str(e), "elapsed": round(ai._step_elapsed, 2)},
            ))

            # --- after_step hook ---
            try:
                await self.after_step(step_name, result)
            except Exception as hook_exc:
                logger.error(f"[Hook] after_step({step_name}) raised: {hook_exc}")

            return result
        finally:
            self._ai = None
            self._ctx.current_step = None

    # ---- Main run loop ----

    def _get_step_failure_policy(self, step_name: str) -> tuple[FailurePolicy, int]:
        """Get failure policy for a step from its @on_failure decorator.

        Returns:
            (policy, max_retries) tuple
        """
        method = getattr(self.__class__, step_name, None)
        if method:
            policy = getattr(method, "_failure_policy", FailurePolicy.ABORT)
            max_retries = getattr(method, "_max_retries", 1)
            return (policy, max_retries)
        return (FailurePolicy.ABORT, 1)

    async def run(self) -> dict:
        """Run the full case: setup → steps → teardown.

        Supports three failure policies per step (via @on_failure decorator):
        - ABORT: stop execution on failure (default)
        - SKIP: skip the failed step and continue
        - RETRY: retry the step up to max_retries times, then abort
        """
        logger.info(f"[Case] {self.__class__.__name__}")

        steps = self.get_step_methods()
        logger.info(f"[Case] Steps: {steps}")

        await event_bus.publish(Event(
            type="execution_started",
            execution_id=self._execution_id,
            data={"case_name": self.__class__.__name__},
        ))

        # --- Setup phase ---
        try:
            await self._ctx.transition("setup")
            await self.setup()
        except Exception as e:
            logger.error(f"[Case] Setup failed: {e}")
            await self._ctx.transition("failed")
            self._ctx.save_snapshot()
            return self._build_report(status="failed", error=f"Setup failed: {e}")

        # --- Running phase ---
        await self._ctx.transition("running")
        success_count = 0
        aborted = False

        for step_name in steps:
            policy, max_retries = self._get_step_failure_policy(step_name)

            # Determine effective attempt limit
            attempt_limit = 1
            if policy == FailurePolicy.RETRY:
                attempt_limit = max_retries + 1

            result = None
            step_succeeded = False

            for attempt in range(attempt_limit):
                if attempt > 0:
                    logger.info(f"[Case] Retrying step {step_name} (attempt {attempt + 1}/{attempt_limit})")

                result = await self.run_step(step_name)
                step_succeeded = result.get("success", False)

                if step_succeeded:
                    break

                # Check on_step_error hook result for retry signal
                hook_result = result.get("_hook_result")
                if hook_result and isinstance(hook_result, StepResult):
                    if hook_result.retry and attempt < attempt_limit - 1:
                        continue  # retry the loop

                if not step_succeeded and policy == FailurePolicy.RETRY and attempt < attempt_limit - 1:
                    continue  # retry via policy

            if step_succeeded:
                success_count += 1
            else:
                # Handle based on policy
                if policy == FailurePolicy.SKIP:
                    logger.warning(f"[Case] Step {step_name} failed, skipping (policy=SKIP)")
                    # Check on_step_error hook for skip signal too
                    hook_result = result.get("_hook_result") if result else None
                    if hook_result and isinstance(hook_result, StepResult) and hook_result.skip:
                        pass  # already handled
                    continue  # move to next step
                else:
                    # ABORT (default) or exhausted retries
                    logger.error(f"[Case] Step {step_name} failed, stopping (policy={policy.value})")
                    aborted = True
                    break

        # --- Teardown phase ---
        try:
            await self._ctx.transition("teardown")
            await self.teardown()
        except Exception as e:
            logger.error(f"[Case] Teardown error (non-fatal): {e}")

        total = len(steps)
        failed = total - success_count
        status = "completed" if failed == 0 else "failed"

        # Final phase transition
        await self._ctx.transition("done" if status == "completed" else "failed")
        self._ctx.save_snapshot()

        report = self._build_report(status=status)

        # Save report to disk (test_results/<timestamp>/report.json + report.md)
        self._save_report(report)

        if status == "completed":
            logger.success(f"[Case] Done: {status} ({success_count}/{total})")
        else:
            logger.error(f"[Case] Done: {status} ({success_count}/{total})")

        await event_bus.publish(Event(
            type="execution_completed",
            execution_id=self._execution_id,
            data={"report": report},
        ))

        return report

    def _build_report(self, status: str, error: str | None = None) -> dict:
        """Build the final execution report."""
        total = len(self.get_step_methods())
        success_count = len(self._ctx.completed_steps)
        report: dict[str, Any] = {
            "case_name": self.__class__.__name__,
            "status": status,
            "total_steps": total,
            "success_count": success_count,
            "failed_count": total - success_count,
            "steps": self._results,
            "phase": self._ctx.phase.value,
            "elapsed_seconds": self._ctx.elapsed_seconds,
        }
        if error:
            report["error"] = error
        return report

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s}s"

    @staticmethod
    def _render_html(report: dict) -> str:
        """Render the report using the Vue + Ant Design SPA template."""
        import base64
        import json

        # Look for the built Vue template
        template_paths = [
            Path(__file__).parent.parent.parent / "report" / "dist" / "index.html",
            Path(__file__).parent / "templates" / "report.html",
        ]
        template_html = None
        for tp in template_paths:
            if tp.exists():
                template_html = tp.read_text(encoding="utf-8")
                break

        if template_html is None:
            return f"<html><body><pre>{json.dumps(report, ensure_ascii=False, indent=2)}</pre></body></html>"

        # Convert screenshot paths to base64 data URIs for inline embedding
        for step in report.get("steps", []):
            for s in step.get("screenshots", []):
                try:
                    with open(s["path"], "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    s["path"] = f"data:image/png;base64,{b64}"
                except Exception:
                    pass

        # Inject report data into the JSON placeholder
        report_json = json.dumps(report, ensure_ascii=False)
        html = template_html.replace('{"placeholder":true}', report_json)
        return html

    def _save_report(self, report: dict) -> None:
        """Save report.json and report.html to the results directory."""
        import json, shutil
        from datetime import datetime

        results_dir = self._results_dir or (self._case_dir / "test_results")
        ts_dir = results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        ts_dir.mkdir(parents=True, exist_ok=True)

        # Copy screenshots to results dir and update paths
        screenshots_dir = ts_dir / "screenshots"
        for step in report.get("steps", []):
            new_paths = []
            for s in step.get("screenshots", []):
                try:
                    screenshots_dir.mkdir(parents=True, exist_ok=True)
                    src = Path(s["path"])
                    dst = screenshots_dir / f"{step['step_id']}_{s['name']}.png"
                    if src.exists():
                        shutil.copy2(src, dst)
                        s["path"] = str(dst)
                        new_paths.append(s)
                except Exception:
                    pass
            step["screenshots"] = new_paths

        # JSON report (machine-readable)
        (ts_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # HTML report (human-readable, rendered from template)
        (ts_dir / "report.html").write_text(
            self._render_html(report),
            encoding="utf-8",
        )

        logger.info(f"[Case] Report saved to {ts_dir}")
