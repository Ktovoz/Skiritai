"""AI Action context — manages replay scripts and agent execution."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Literal

from skiritai.core.agent_loop import run_agent
from skiritai.core.script_generator import generate_replay_script
from skiritai.logger import logger

ActionMode = Literal["auto", "explore", "replay"]

# ---------------------------------------------------------------------------
# Replay script integrity
# ---------------------------------------------------------------------------

SCRIPT_HASH_SUFFIX = ".sha256"

# AST nodes allowed in replay scripts — blocks imports, exec, eval, etc.
_ALLOWED_AST_NODES = frozenset({
    ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.arguments, ast.arg,
    ast.Expr, ast.Constant, ast.Name, ast.Load, ast.Store, ast.Del,
    ast.Attribute, ast.Call, ast.keyword, ast.Assign, ast.AnnAssign,
    ast.AugAssign, ast.Return, ast.Pass, ast.Raise, ast.Assert,
    ast.If, ast.For, ast.While, ast.Break, ast.Continue, ast.Try,
    ast.ExceptHandler, ast.With, ast.withitem, ast.Compare, ast.BoolOp,
    ast.BinOp, ast.UnaryOp, ast.IfExp, ast.Dict, ast.List, ast.Tuple,
    ast.Set, ast.Subscript, ast.Slice, ast.Starred, ast.JoinedStr,
    ast.FormattedValue, ast.Await, ast.Attribute, ast.Global, ast.Nonlocal,
})
_FORBIDDEN_BUILTINS = frozenset({
    "exec", "eval", "compile", "__import__", "open", "input",
    "breakpoint", "memoryview", "help",
})


def _validate_replay_ast(tree: ast.AST) -> None:
    """Validate that a replay script AST contains only safe node types.

    Raises ValueError if unsafe constructs (imports, exec, eval, etc.) are found.
    """
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_AST_NODES:
            raise ValueError(
                f"Unsafe AST node in replay script: {type(node).__name__}. "
                f"Script may only use basic control flow and function calls."
            )
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("Import statements are not allowed in replay scripts")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_BUILTINS:
                raise ValueError(
                    f"Forbidden builtin function '{node.func.id}' in replay script"
                )


def _compute_script_hash(content: str) -> str:
    """Compute SHA256 hash of script content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _verify_script(script_path: Path) -> bool:
    """Verify the script file matches its stored hash.

    Returns True only if the hash file exists and matches.
    Scripts without hash files are rejected (backward compatibility:
    re-run the step in explore mode to regenerate with hash).
    """
    hash_path = Path(str(script_path) + SCRIPT_HASH_SUFFIX)
    if not hash_path.exists():
        logger.warning(
            f"[Security] Replay script has no integrity hash: {script_path}. "
            f"Re-run this step in explore or auto mode to generate the hash."
        )
        return False

    content = script_path.read_text(encoding="utf-8")
    expected = hash_path.read_text(encoding="utf-8").strip()
    actual = _compute_script_hash(content)
    if actual != expected:
        logger.error(
            f"[Security] Replay script hash mismatch: {script_path}. "
            f"Expected {expected[:16]}..., got {actual[:16]}..."
        )
        return False
    return True


def _save_script_hash(script_path: Path, script_content: str) -> None:
    """Save a SHA256 hash alongside the script for later verification."""
    hash_path = Path(str(script_path) + SCRIPT_HASH_SUFFIX)
    hash_path.write_text(_compute_script_hash(script_content), encoding="utf-8")


class AIContext:
    """Context for AI actions in a test case.

    Each action either replays a saved script or calls the AI agent to explore.
    After exploration, a replay script is generated for future use.

    In ``auto`` mode, if replay fails the context automatically falls back to
    exploration so the step can still succeed.

    Direct perception methods (analyze_page, get_page_info) can be called
    before action() to pre-load page data. The stored data is automatically
    injected into subsequent action() calls so the AI doesn't need to
    re-discover the page structure.
    """

    def __init__(
            self,
            page: Any,
            case_dir: Path,
            step_id: str,
            on_log: Callable | None = None,
            default_mode: ActionMode = "auto",
            execution_id: str = "default",
            max_steps: int = 20,
            llm=None,
    ):
        self.page = page
        self.case_dir = case_dir
        self.step_id = step_id
        self.on_log = on_log
        self.default_mode = default_mode
        self.execution_id = execution_id
        self.max_steps = max_steps
        self._llm = llm
        self.scripts_dir = case_dir / "scripts"
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self._last_result: dict | None = None
        self._page_analysis: dict | None = None
        self._page_info: str = ""
        self._screenshots: list[dict] = []
        self._verifications: list[dict] = []
        self._step_started_at: float = 0.0
        self._step_elapsed: float = 0.0

    @property
    def script_path(self) -> Path:
        """Path to the replay script for this step."""
        return self.scripts_dir / f"{self.step_id}.py"

    def has_replay(self) -> bool:
        """Check if a replay script exists for this step."""
        return self.script_path.exists()

    # ---- Direct perception methods (no AI reasoning needed) ----

    async def analyze_page(self) -> dict:
        """Directly analyze the page DOM and store the result.

        Returns all visible inputs, buttons, links, and text content.
        The result is stored and automatically injected into the next
        action() call, so the AI doesn't need to call analyze_page itself.
        """
        from skiritai.core.tools import analyze_page as _tool, set_page as _set_page
        _set_page(self.page)
        result = await _tool.ainvoke({})
        try:
            self._page_analysis = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            self._page_analysis = {"raw": str(result)}
        return self._page_analysis

    async def get_page_info(self) -> str:
        """Get page title, URL, and text summary. Stores result for injection."""
        from skiritai.core.tools import get_page_info as _tool, set_page as _set_page
        _set_page(self.page)
        result = await _tool.ainvoke({})
        self._page_info = result
        return result

    async def screenshot(self, name: str = "screenshot") -> str:
        """Capture a page screenshot at a specific point in the test.

        Args:
            name: Screenshot name (without extension). Will be saved as <name>.png.
                  Use descriptive names like 'homepage', 'search_result'.

        Returns the file path of the saved screenshot.

        Usage:
            await self.ai.screenshot("homepage_loaded")
        """
        import base64
        import tempfile
        path = str(Path(tempfile.gettempdir()) / f"skiritai_{self.step_id}_{name}.png")
        await self.page.screenshot(path=path, full_page=True)
        self._screenshots.append({"name": name, "path": path, "timestamp": self._step_started_at})
        logger.info(f"[Screenshot] {self.step_id}/{name} saved")
        return path

    async def verify(self, assertion: str, take_screenshot: bool = True) -> dict:
        """Run an AI-powered assertion to verify a condition on the page.

        Unlike action(), this is designed for boolean pass/fail checks.
        On pass: logs with logger.success (green).
        On fail: logs with logger.warning (yellow) — does NOT interrupt the test.

        Args:
            assertion: Natural language assertion, e.g. "页面标题包含 'Blog'"
            take_screenshot: Automatically capture screenshot on failure (default True)

        Returns:
            dict with keys: passed (bool), reason (str), screenshot (str|None)

        Usage:
            result = await self.ai.verify("页面显示至少3篇文章")
            if not result["passed"]:
                print("Assertion failed but test continues")
        """
        from skiritai.core.agent_loop import run_agent as _run_agent

        prompt = (
            f"你是一个断言验证器。请判断以下断言是否为真。\n\n"
            f"断言: {assertion}\n\n"
            f"请先分析当前页面的实际状态，然后给出判断。"
            f"用 JSON 格式回复: {{\"passed\": true/false, \"reason\": \"判断理由\"}}"
        )
        try:
            result = await _run_agent(
                page=self.page,
                task_description=prompt,
                on_log=self.on_log,
                execution_id=self.execution_id,
                case_dir=self.case_dir,
                max_steps=self.max_steps,
                llm=self._llm,
            )
            # Try to parse JSON from the result
            import json as _json
            summary = result.get("summary", "")
            passed = False
            reason = summary
            try:
                # Find JSON in the summary
                start = summary.find("{")
                end = summary.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = _json.loads(summary[start:end])
                    passed = parsed.get("passed", False)
                    reason = parsed.get("reason", summary)
            except _json.JSONDecodeError:
                passed = result.get("success", False)
                reason = summary

            screenshot_path = None
            if not passed and take_screenshot:
                try:
                    screenshot_path = await self.screenshot(f"verify_fail_{self.step_id}")
                except Exception:
                    pass

            self._verifications.append({
                "assertion": assertion,
                "passed": passed,
                "reason": reason,
                "screenshot": screenshot_path,
            })

            if passed:
                logger.success(f"[Verify] PASS: {assertion[:80]}")
            else:
                logger.warning(f"[Verify] FAIL: {assertion[:80]} — {reason[:120]}")

            return {"passed": passed, "reason": reason, "screenshot": screenshot_path}
        except Exception as e:
            logger.error(f"[Verify] Error: {e}")
            self._verifications.append({
                "assertion": assertion,
                "passed": False,
                "reason": str(e),
                "screenshot": None,
            })
            return {"passed": False, "reason": str(e), "screenshot": None}

    # ---- Main action entry ----

    async def action(self, description: str, mode: ActionMode | None = None) -> dict:
        """Execute an action with configurable mode.

        Args:
            description: Natural language description of what to do.
                Use pure natural language — no need to specify which tools
                to use. If analyze_page() or get_page_info() were called
                before, their data is automatically available as context.

            mode: Execution mode override:
                - None      — use default_mode from @step_mode decorator or "auto"
                - "auto"    — replay if script exists; on replay failure, fallback to explore
                - "explore" — always explore with AI, overwrite existing script
                - "replay"  — always replay, error if no script exists

        Returns:
            dict with success, summary, steps
        """
        # Inject pre-loaded perception data as context for the AI
        if self._page_analysis or self._page_info:
            prelude = "以下是你当前所在页面的预分析数据（已通过 analyze_page/get_page_info 获取），请直接使用这些信息完成任务，无需再次调用分析工具：\n\n"
            if self._page_analysis:
                prelude += f"--- 页面结构分析 ---\n{json.dumps(self._page_analysis, ensure_ascii=False, indent=2)}\n\n"
            if self._page_info:
                prelude += f"--- 页面基本信息 ---\n{self._page_info}\n\n"
            description = prelude + "任务：" + description

        mode = mode or self.default_mode
        if mode == "explore":
            result = await self._explore(description)
        elif mode == "replay":
            if not self.has_replay():
                raise FileNotFoundError(
                    f"No replay script for step '{self.step_id}': {self.script_path}. "
                    f"Run in explore mode first to generate the script."
                )
            result = await self._replay()
        else:  # auto
            if self.has_replay():
                result = await self._replay()
                if not result.get("success"):
                    logger.warning(
                        f"[Auto] {self.step_id}: replay failed, falling back to explore"
                    )
                    result = await self._explore(description)
            else:
                result = await self._explore(description)
        self._last_result = result
        return result

    async def _replay(self) -> dict:
        """Execute the saved replay script directly without AI reasoning.

        Validates integrity (SHA256 hash) and structure (AST whitelist) before
        execution. Uses a restricted builtins namespace to sandbox the script.
        """
        logger.info(f"[Replay] {self.step_id}: executing {self.script_path}")

        if not _verify_script(self.script_path):
            return {
                "success": False,
                "summary": "回放脚本完整性校验失败 — 脚本可能已被篡改。请用 explore 模式重新生成。",
                "steps": [],
            }

        try:
            script_content = self.script_path.read_text(encoding="utf-8")

            # AST validation — block imports, exec, eval, etc.
            tree = ast.parse(script_content, filename=str(self.script_path))
            _validate_replay_ast(tree)

            # Restricted builtins — safe subset for replay scripts
            safe_builtins = {
                k: v for k, v in __builtins__.items()  # type: ignore[attr-defined]
                if k not in _FORBIDDEN_BUILTINS
            }
            exec_globals: dict[str, Any] = {
                "__builtins__": safe_builtins,
            }

            exec(script_content, exec_globals)

            if "run" in exec_globals:
                await exec_globals["run"](self.page, self.page.context)

            logger.info(f"[Replay] {self.step_id}: completed successfully")
            return {
                "success": True,
                "summary": "回放脚本执行成功",
                "steps": [{"action": "replay", "script": str(self.script_path)}],
            }

        except Exception as e:
            logger.error(f"[Replay] {self.step_id} failed: {e}")
            return {
                "success": False,
                "summary": f"回放脚本执行失败: {e}",
                "steps": [],
            }

    async def _explore(self, description: str) -> dict:
        """Use AI agent to explore and generate replay script."""
        logger.info(f"[Explore] {self.step_id}: {description!r}")

        result = await run_agent(
            page=self.page,
            task_description=description,
            on_log=self.on_log,
            execution_id=self.execution_id,
            case_dir=self.case_dir,
            max_steps=self.max_steps,
            llm=self._llm,
        )

        if result.get("success"):
            script = generate_replay_script(self.step_id, result.get("steps", []))
            self.script_path.write_text(script, encoding="utf-8")
            _save_script_hash(self.script_path, script)
            logger.info(f"[Explore] {self.step_id}: script saved to {self.script_path}")

        return result
