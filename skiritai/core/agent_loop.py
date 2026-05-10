"""Agent loop powered by LangGraph ReAct agent."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langgraph.prebuilt import create_react_agent

from skiritai.core.llm_retry import retry_async
from skiritai.core.tool_registry import ToolRegistry
from skiritai.core.tools import set_page
from skiritai.events import Event, event_bus
from skiritai.llm import get_provider
from skiritai.logger import logger

# Tools that are read-only perception — excluded from replay scripts
PERCEPTION_TOOLS = {"page_perceive", "find_element", "analyze_page", "get_page_info"}

# ---------------------------------------------------------------------------
# Default system prompt (used when no custom prompt is provided)
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """你是一个浏览器自动化测试 Agent。你通过调用工具来操作浏览器完成测试任务。

工作流程：
1. 先用 analyze_page 分析页面的真实 DOM 结构（返回所有可见输入框、按钮、链接）
2. 用 get_page_info 获取页面标题、URL 和文本摘要
3. 根据 analyze_page 返回的实际选择器，调用操作工具（click、fill、navigate 等）
4. 操作后再次用 analyze_page 或 get_page_info 验证结果
5. 重复直到任务完成

元素定位策略（按优先级）：
- 优先用 analyze_page 获取页面上所有可交互元素的真实选择器
- analyze_page 返回的是当前页面的实际 DOM，选择器保证有效
- 切勿使用训练数据中已知的选择器（如 #kw, #su），这些可能在页面更新后已失效
- 选择器应该来自 analyze_page 的实时分析结果

重要规则：
- 每次进入新页面后，必须先调用 analyze_page 了解页面真实结构
- 找不到元素时，用 analyze_page 重新分析，而不是重试已知选择器
- 如果操作失败，分析原因并换一种方式（如用 click_force 代替 click，或用 type_text 代替 fill）
- 当任务完成时，直接用自然语言总结结果即可
"""


def load_system_prompt(case_dir: Path | None = None) -> str:
    """Resolve the system prompt with the following priority:

    1. Case-level prompt file: ``<case_dir>/prompt.md`` or ``<case_dir>/prompt.txt``
    2. Environment variable ``SYSTEM_PROMPT_FILE`` pointing to a file
    3. Environment variable ``SYSTEM_PROMPT`` containing the prompt text
    4. Built-in ``DEFAULT_SYSTEM_PROMPT``
    """
    # 1. Case-level prompt file
    if case_dir is not None:
        for name in ("prompt.md", "prompt.txt"):
            p = case_dir / name
            if p.is_file():
                prompt = p.read_text(encoding="utf-8").strip()
                if prompt:
                    logger.info(f"[Agent] Using case-level system prompt from {p}")
                    return prompt

    # 2. SYSTEM_PROMPT_FILE env var
    prompt_file = os.getenv("SYSTEM_PROMPT_FILE")
    if prompt_file:
        p = Path(prompt_file)
        if p.is_file():
            prompt = p.read_text(encoding="utf-8").strip()
            if prompt:
                logger.info(f"[Agent] Using system prompt from env file: {p}")
                return prompt

    # 3. SYSTEM_PROMPT env var (inline text)
    inline = os.getenv("SYSTEM_PROMPT")
    if inline and inline.strip():
        logger.info("[Agent] Using inline system prompt from env var")
        return inline.strip()

    # 4. Default
    return DEFAULT_SYSTEM_PROMPT


# Module-level default prompt for backward compatibility
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


def register_all_tools() -> None:
    """Explicitly register all tool modules.

    Must be called once at startup (or before building the agent).
    This replaces relying on import side-effects.
    """
    import skiritai.core.tools  # noqa: F401 — registers action tools
    import skiritai.core.perception  # noqa: F401 — registers perception tools


def _build_llm():
    provider = get_provider()
    return provider.build()


def build_agent(system_prompt: str | None = None):
    """Build a LangGraph ReAct agent with Playwright tools + perception tools.

    Args:
        system_prompt: Custom system prompt. If None, uses the default prompt.
    """
    llm = _build_llm()
    registry = ToolRegistry()
    tools = registry.get_all()
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt or SYSTEM_PROMPT,
    )


async def run_agent(
        page: Any,
        task_description: str,
        url: str = "",
        on_log: Any = None,
        execution_id: str = "default",
        case_dir: Path | None = None,
) -> dict:
    """
    Run the LangGraph ReAct agent on a task.

    Args:
        page: Playwright Page object
        task_description: What to accomplish
        url: Optional URL to navigate to first
        on_log: Optional callback for real-time log streaming
        execution_id: Execution identifier for event publishing
        case_dir: Optional case directory for loading case-level system prompt

    Returns:
        dict with keys: success, summary, steps, token_usage
    """
    set_page(page)

    # Resolve system prompt (case-level > env > default)
    system_prompt = load_system_prompt(case_dir)
    agent = build_agent(system_prompt=system_prompt)

    if url:
        user_msg = f"请先导航到 {url}，然后执行以下任务：\n{task_description}"
    else:
        user_msg = f"请执行以下测试任务：\n{task_description}"

    steps: list[dict] = []
    final_summary = ""
    success = False
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    async def _stream_once() -> None:
        """Consume the agent stream once, populating outer-scope variables."""
        nonlocal steps, final_summary, success
        # Reset per-attempt state but keep token_usage cumulative
        steps = []
        final_summary = ""

        async for event in agent.astream(
                {"messages": [{"role": "user", "content": user_msg}]},
                config={"recursion_limit": 20},
        ):
            _accumulate_token_usage(event, token_usage)

            if "agent" in event:
                msg = event["agent"].get("messages", [])
                if msg:
                    last = msg[-1]
                    if hasattr(last, "tool_calls") and last.tool_calls:
                        for tc in last.tool_calls:
                            tool_name = tc["name"]
                            tool_args = tc.get("args", {})
                            logger.info(f"[Agent] Tool call: {tool_name}({tool_args})")
                            if on_log:
                                await on_log(f"调用工具: {tool_name}({tool_args})")
                            await event_bus.publish(Event(
                                type="tool_called",
                                execution_id=execution_id,
                                data={"tool_name": tool_name, "tool_args": tool_args},
                            ))
                            steps.append({
                                "action": tool_name,
                                "args": tool_args,
                            })
                    elif hasattr(last, "content") and last.content:
                        final_summary = last.content
                        steps.append({"action": "response", "content": last.content})

            if "tools" in event:
                msg = event["tools"].get("messages", [])
                if msg:
                    last = msg[-1]
                    result_text = last.content[:500] if hasattr(last, "content") else ""
                    if steps and steps[-1].get("action") != "response":
                        steps[-1]["result"] = result_text

        # Determine success from the last tool call or summary
        if steps:
            last_step = steps[-1]
            if last_step.get("action") == "task_complete":
                success = last_step.get("args", {}).get("success", False)
                final_summary = last_step.get("args", {}).get("summary", "")
            else:
                success = True
                if not final_summary:
                    final_summary = "任务执行完成"

    try:
        await retry_async(
            _stream_once,
            operation_name=f"agent task: {task_description[:50]}",
        )
    except Exception as e:
        logger.error(f"[Agent] Error after retries: {e}")
        return {
            "success": False,
            "summary": f"Agent 执行失败: {e}",
            "steps": steps,
            "token_usage": token_usage,
        }

    logger.info(f"[Agent] Done: success={success} summary={final_summary[:100]} "
                f"tokens={token_usage['total_tokens']}")
    return {
        "success": success,
        "summary": final_summary,
        "steps": steps,
        "token_usage": token_usage,
    }


def _accumulate_token_usage(event: dict, token_usage: dict) -> None:
    """Extract token usage metadata from LangGraph streaming events."""
    try:
        # LangGraph stores usage metadata on agent messages
        for key in ("agent",):
            if key not in event:
                continue
            messages = event[key].get("messages", [])
            for msg in messages:
                usage = getattr(msg, "usage_metadata", None)
                if usage and isinstance(usage, dict):
                    token_usage["prompt_tokens"] += usage.get("input_tokens", 0)
                    token_usage["completion_tokens"] += usage.get("output_tokens", 0)
                    token_usage["total_tokens"] += usage.get("total_tokens", 0)

                # Fallback: response_metadata (some LangChain versions)
                resp_meta = getattr(msg, "response_metadata", None)
                if resp_meta and isinstance(resp_meta, dict):
                    token_info = resp_meta.get("token_usage", {})
                    if token_info:
                        token_usage["prompt_tokens"] += token_info.get("prompt_tokens", 0)
                        token_usage["completion_tokens"] += token_info.get("completion_tokens", 0)
                        token_usage["total_tokens"] += token_info.get("total_tokens", 0)
    except Exception:
        pass  # token tracking is best-effort
