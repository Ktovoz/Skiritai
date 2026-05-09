"""Agent loop powered by LangGraph ReAct agent."""
from __future__ import annotations

from typing import Any

from langgraph.prebuilt import create_react_agent

from app.engine.event_bus import Event, event_bus
from app.engine.llm import get_provider
from app.engine.tool_registry import ToolRegistry
import app.engine.tools  # triggers Playwright tool registration
import app.engine.perception  # triggers perception tool registration
from app.engine.tools import set_page
from app.logger import logger

# Tools that are read-only perception — excluded from replay scripts
PERCEPTION_TOOLS = {"page_perceive", "find_element"}

SYSTEM_PROMPT = """你是一个浏览器自动化测试 Agent。你通过调用工具来操作浏览器完成测试任务。

工作流程：
1. 用 page_perceive 深度分析页面 DOM 结构，了解所有可交互元素
2. 如果需要查找特定元素，用 find_element 自然语言搜索
3. 用 get_page_info 获取页面标题和 URL
4. 根据感知结果，调用操作工具（click、fill、navigate 等）执行操作
5. 操作后再用 page_perceive 或 get_page_info 验证结果
6. 重复直到任务完成

元素定位策略（按优先级）：
- 优先用 page_perceive 获取完整页面结构，它会返回每个元素的精确 CSS 选择器
- 用 find_element("描述") 模糊搜索元素，返回最佳匹配的选择器
- 也可以直接用 CSS 选择器，如 '#id', '.class', 'text=文本'

重要规则：
- 每次进入新页面或操作后，先用感知工具了解当前状态
- 感知工具（page_perceive、find_element）是只读的，不会修改页面
- 如果元素找不到，用 page_perceive 重新分析页面
- 如果操作失败，分析原因并重试或换一种方式
- 当任务完成时，直接用自然语言总结结果即可
"""


def _build_llm():
    provider = get_provider()
    return provider.build()


def build_agent():
    """Build a LangGraph ReAct agent with Playwright tools + perception tools."""
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
