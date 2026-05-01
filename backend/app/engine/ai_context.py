"""AI Action context - manages replay scripts and agent execution."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Literal

from app.engine.agent_loop import run_agent
from app.engine.tools import set_page
from app.logger import logger

ActionMode = Literal["auto", "explore", "replay"]


class AIContext:
    """Context for AI actions in a test case.

    Each action either replays a saved script or calls the AI agent to explore.
    After exploration, a replay script is generated for future use.
    """

    def __init__(
        self,
        page: Any,
        case_dir: Path,
        step_id: str,
        on_log: Callable | None = None,
        default_mode: ActionMode = "auto",
        execution_id: str = "default",
    ):
        self.page = page
        self.case_dir = case_dir
        self.step_id = step_id
        self.on_log = on_log
        self.default_mode = default_mode
        self.execution_id = execution_id
        self.scripts_dir = case_dir / "scripts"
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self._last_result: dict | None = None

    @property
    def script_path(self) -> Path:
        """Path to the replay script for this step."""
        return self.scripts_dir / f"{self.step_id}.py"

    def has_replay(self) -> bool:
        """Check if a replay script exists for this step."""
        return self.script_path.exists()

    async def action(self, description: str, mode: ActionMode | None = None) -> dict:
        """Execute an action with configurable mode.

        Args:
            description: Natural language description of what to do
            mode: Execution mode override:
                - None      — use default_mode from @step_mode decorator or "auto"
                - "auto"    — replay if script exists, otherwise explore
                - "explore" — always explore with AI, overwrite existing script
                - "replay"  — always replay, error if no script exists

        Returns:
            dict with success, summary, steps
        """
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
            else:
                result = await self._explore(description)
        self._last_result = result
        return result

    async def _replay(self) -> dict:
        """Execute the saved replay script directly without AI reasoning."""
        logger.info(f"[Replay] {self.step_id}: executing {self.script_path}")

        try:
            # Read and execute the script directly
            script_content = self.script_path.read_text(encoding="utf-8")

            # Create execution context
            exec_globals = {
                "page": self.page,
                "context": self.page.context,
            }

            # Execute the script
            exec(script_content, exec_globals)

            # If there's a run function, call it
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
        )

        if result.get("success"):
            # Generate and save replay script
            script = self._generate_script(result.get("steps", []))
            self.script_path.write_text(script, encoding="utf-8")
            logger.info(f"[Explore] {self.step_id}: script saved to {self.script_path}")

        return result

    def _generate_script(self, agent_steps: list[dict]) -> str:
        """Generate a replay script from agent's tool-calling history."""
        lines = [
            f"# Auto-generated replay script",
            f"# Step: {self.step_id}",
            f"",
            f"async def run(page, context):",
        ]

        action_lines = []
        for step in agent_steps:
            action = step.get("action", "")
            args = step.get("args", {})

            if action == "navigate":
                url = args.get("url", "")
                action_lines.append(f'    await page.goto("{url}")')
                action_lines.append(f'    await page.wait_for_load_state("networkidle")')

            elif action == "click":
                selector = args.get("selector", "")
                action_lines.append(f'    await page.click("{selector}")')

            elif action == "click_force":
                selector = args.get("selector", "")
                action_lines.append(f'    await page.click("{selector}", force=True)')

            elif action == "fill":
                selector = args.get("selector", "")
                text = args.get("text", "")
                action_lines.append(f'    await page.fill("{selector}", "{text}")')

            elif action == "type_text":
                selector = args.get("selector", "")
                text = args.get("text", "")
                action_lines.append(f'    await page.locator("{selector}").press_sequentially("{text}")')

            elif action == "focus":
                selector = args.get("selector", "")
                action_lines.append(f'    await page.locator("{selector}").focus()')

            elif action == "wait_for":
                selector = args.get("selector", "")
                timeout = args.get("timeout", 5000)
                action_lines.append(f'    await page.wait_for_selector("{selector}", timeout={timeout})')

            elif action == "scroll":
                direction = args.get("direction", "down")
                amount = args.get("amount", 500)
                y = amount if direction == "down" else -amount
                action_lines.append(f'    await page.mouse.wheel(0, {y})')

            elif action == "eval_js":
                expression = args.get("expression", "")
                # Escape quotes in the expression
                escaped = expression.replace('"', '\\"')
                action_lines.append(f'    await page.evaluate("{escaped}")')

            elif action == "select_option":
                selector = args.get("selector", "")
                value = args.get("value", "")
                action_lines.append(f'    await page.select_option("{selector}", "{value}")')

            elif action == "hover":
                selector = args.get("selector", "")
                action_lines.append(f'    await page.hover("{selector}")')

        # If no actionable steps, add a pass statement
        if not action_lines:
            action_lines.append("    pass")

        lines.extend(action_lines)
        return "\n".join(lines)
