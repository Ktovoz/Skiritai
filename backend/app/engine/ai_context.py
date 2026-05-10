"""AI Action context — manages replay scripts and agent execution."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

from app.engine.agent_loop import run_agent
from app.engine.script_generator import generate_replay_script
from app.logger import logger

ActionMode = Literal["auto", "explore", "replay"]


class AIContext:
    """Context for AI actions in a test case.

    Each action either replays a saved script or calls the AI agent to explore.
    After exploration, a replay script is generated for future use.

    In ``auto`` mode, if replay fails the context automatically falls back to
    exploration so the step can still succeed.
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
                - "auto"    — replay if script exists; on replay failure, fallback to explore
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
        """Execute the saved replay script directly without AI reasoning."""
        logger.info(f"[Replay] {self.step_id}: executing {self.script_path}")

        try:
            script_content = self.script_path.read_text(encoding="utf-8")

            exec_globals: dict[str, Any] = {
                "__builtins__": __builtins__,
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
        )

        if result.get("success"):
            script = generate_replay_script(self.step_id, result.get("steps", []))
            self.script_path.write_text(script, encoding="utf-8")
            logger.info(f"[Explore] {self.step_id}: script saved to {self.script_path}")

        return result
