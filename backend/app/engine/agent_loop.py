"""Agent loop powered by LangGraph ReAct agent."""
from __future__ import annotations

from typing import Any

from langgraph.prebuilt import create_react_agent

from app.engine.event_bus import Event, event_bus
from app.engine.llm import get_provider
from app.engine.tool_registry import ToolRegistry
import app.engine.tools  # triggers tool registration via @register_tool
from app.engine.tools import set_page
from app.logger import logger

SYSTEM_PROMPT = """你是一个浏览器自动化测试 Agent。你通过调用工具来操作浏览器完成测试任务。

工作流程：
1. 用 get_page_info 获取当前页面状态
2. 分析页面文本和结构，决定下一步操作
3. 调用相应工具执行操作
4. 用 get_text 或 get_page_info 确认操作结果
5. 重复直到任务完成

重要规则：
- 用 get_page_info 获取页面标题、URL 和文本摘要来了解页面状态
- 用 get_text 获取特定元素的文本内容
- 如果元素找不到，尝试用 wait_for 等待
- 如果操作失败，分析原因并重试或换一种方式
- 用 CSS 选择器定位元素，如 '#id', '.class', 'text=文本'
- 当任务完成时，直接用自然语言总结结果即可
"""


def _build_llm():
    provider = get_provider()
    return provider.build()


def build_agent():
    """Build a LangGraph ReAct agent with Playwright tools."""
    llm = _build_llm()
    registry = ToolRegistry()
    tools = registry.get_all()
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )


async def run_agent(
    page: Any,
    task_description: str,
    url: str = "",
    on_log: Any = None,
    execution_id: str = "default",
) -> dict:
    """
    Run the LangGraph ReAct agent on a task.

    Args:
        page: Playwright Page object
        task_description: What to accomplish
        url: Optional URL to navigate to first
        on_log: Optional callback for real-time log streaming
        execution_id: Execution identifier for event publishing

    Returns:
        dict with keys: success, summary, steps
    """
    set_page(page)

    agent = build_agent()

    if url:
        user_msg = f"请先导航到 {url}，然后执行以下任务：\n{task_description}"
    else:
        user_msg = f"请执行以下测试任务：\n{task_description}"

    steps = []
    final_summary = ""
    success = False

    try:
        async for event in agent.astream(
            {"messages": [{"role": "user", "content": user_msg}]},
            config={"recursion_limit": 20},
        ):
            # Process agent events
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
                # Agent finished without explicit task_complete — treat as success if no errors
                success = True
                if not final_summary:
                    final_summary = "任务执行完成"

    except Exception as e:
        logger.error(f"[Agent] Error: {e}")
        return {"success": False, "summary": f"Agent 执行失败: {e}", "steps": steps}

    logger.info(f"[Agent] Done: success={success} summary={final_summary[:100]}")
    return {
        "success": success,
        "summary": final_summary,
        "steps": steps,
    }
