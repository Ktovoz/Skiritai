"""Unit tests for agent_loop — agent building, execution, and event publishing."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# Helpers
# ============================================================

def _make_agent_event(data: dict) -> dict:
    """Simulate a LangGraph agent astream event for 'agent' key."""
    msg = MagicMock()
    for key, value in data.items():
        setattr(msg, key, value)
    msg_dict = MagicMock()
    msg_dict.__getitem__ = lambda self, k, default=None: [msg] if k == "messages" else default
    return {"agent": msg_dict}


def _make_tools_event(content: str = "OK") -> dict:
    """Simulate a LangGraph agent astream event for 'tools' key."""
    msg = MagicMock()
    msg.content = content
    msg_dict = {"messages": [msg]}
    return {"tools": msg_dict}


# ============================================================
# 1. build_agent Tests
# ============================================================

class TestBuildAgent:
    """Test build_agent() creates a valid ReAct agent."""

    def test_build_agent_returns_agent(self):
        from skiritai.llm.registry import _PROVIDERS
        from skiritai.llm.openai_provider import OpenAIProvider

        # Register a mock provider
        mock_llm = MagicMock()
        mock_provider = MagicMock(spec=OpenAIProvider)
        mock_provider.build.return_value = mock_llm
        mock_provider.name = "openai"

        _PROVIDERS["mock_test"] = type(mock_provider)

        with patch("skiritai.core.agent_loop.get_provider", return_value=mock_provider):
            with patch(
                    "skiritai.core.agent_loop.create_react_agent"
            ) as mock_create:
                from skiritai.core.agent_loop import build_agent

                result = build_agent()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["model"] is mock_llm
                assert "tools" in call_kwargs
                assert "prompt" in call_kwargs

                # Tools should include Playwright and perception tools
                tool_names = [t.name for t in call_kwargs["tools"]]
                assert "navigate" in tool_names
                assert "click" in tool_names
                assert "fill" in tool_names

        # Cleanup
        _PROVIDERS.pop("mock_test", None)

    def test_build_agent_includes_perception_tools(self):
        from skiritai.llm.registry import _PROVIDERS
        from skiritai.llm.openai_provider import OpenAIProvider

        # Register tools before building (refactored: tools no longer auto-import)
        from skiritai.core.agent_loop import register_all_tools
        register_all_tools()

        mock_llm = MagicMock()
        mock_provider = MagicMock(spec=OpenAIProvider)
        mock_provider.build.return_value = mock_llm
        _PROVIDERS["mock_test"] = type(mock_provider)

        try:
            with patch("skiritai.core.agent_loop.get_provider", return_value=mock_provider):
                with patch(
                        "skiritai.core.agent_loop.create_react_agent"
                ) as mock_create:
                    from skiritai.core.agent_loop import build_agent
                    build_agent()

                    call_kwargs = mock_create.call_args.kwargs
                    tool_names = [t.name for t in call_kwargs["tools"]]
                    assert "page_perceive" in tool_names
                    assert "find_element" in tool_names
        finally:
            _PROVIDERS.pop("mock_test", None)


# ============================================================
# 2. run_agent Execution Tests
# ============================================================

class TestRunAgent:
    """Test run_agent with mocked LangGraph agent astream."""

    async def _mock_agent_astream(self, _input, **_kwargs):
        """Default mock: single navigate step, then success."""
        # Agent calls navigate
        msg1 = MagicMock()
        msg1.tool_calls = [{"name": "navigate", "args": {"url": "http://example.com"}}]
        yield {"agent": {"messages": [msg1]}}

        # Tools respond with result
        msg2 = MagicMock()
        msg2.content = "Navigated to http://example.com"
        yield {"tools": {"messages": [msg2]}}

        # Agent responds with completion
        msg3 = MagicMock()
        msg3.content = "Successfully navigated"
        msg3.tool_calls = None
        yield {"agent": {"messages": [msg3]}}

    def test_run_agent_success(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()
        mock_page.url = "http://localhost"

        with patch(
                "skiritai.core.agent_loop.build_agent"
        ) as mock_build:
            mock_agent = MagicMock()
            mock_agent.astream = self._mock_agent_astream
            mock_build.return_value = mock_agent

            with patch("skiritai.core.agent_loop.set_page") as mock_set_page:
                result = asyncio.run(
                    run_agent(mock_page, "navigate to site", execution_id="e1")
                )

        mock_set_page.assert_called_once_with(mock_page)
        assert result["success"] is True
        assert result["summary"] == "Successfully navigated"
        assert len(result["steps"]) >= 1
        assert result["steps"][0]["action"] == "navigate"

    def test_run_agent_with_url_parameter(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def capture_input(_input, **_kwargs):
                # Capture the user message to verify URL is included
                messages = _input["messages"]
                user_content = messages[0]["content"]
                assert "http://example.com" in user_content
                assert "导航" in user_content

                # Yield a completion
                msg = MagicMock()
                msg.content = "done"
                msg.tool_calls = None
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = capture_input
            mock_build.return_value = mock_agent

            result = asyncio.run(
                run_agent(
                    mock_page,
                    task_description="click the button",
                    url="http://example.com",
                )
            )

        assert result["success"] is True

    def test_run_agent_without_url(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def capture_input(_input, **_kwargs):
                messages = _input["messages"]
                user_content = messages[0]["content"]
                assert "请执行以下测试任务" in user_content
                assert "click the button" in user_content

                msg = MagicMock()
                msg.content = "done"
                msg.tool_calls = None
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = capture_input
            mock_build.return_value = mock_agent

            result = asyncio.run(
                run_agent(mock_page, "click the button")
            )

        assert result["success"] is True

    def test_run_agent_task_complete_detection(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def stream(*args, **kwargs):
                msg = MagicMock()
                msg.tool_calls = [
                    {
                        "name": "task_complete",
                        "args": {"success": True, "summary": "All tests passed"},
                    }
                ]
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = stream
            mock_build.return_value = mock_agent

            result = asyncio.run(run_agent(mock_page, "run tests"))
            assert result["success"] is True
            assert result["summary"] == "All tests passed"

    def test_run_agent_task_complete_with_failure(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def stream(*args, **kwargs):
                msg = MagicMock()
                msg.tool_calls = [
                    {
                        "name": "task_complete",
                        "args": {"success": False, "summary": "Element not found"},
                    }
                ]
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = stream
            mock_build.return_value = mock_agent

            result = asyncio.run(run_agent(mock_page, "run tests"))
            assert result["success"] is False
            assert "Element not found" in result["summary"]

    def test_run_agent_exception_handling(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def failing_stream(*args, **kwargs):
                raise RuntimeError("unexpected agent failure")
                yield  # never reached

            mock_agent.astream = failing_stream
            mock_build.return_value = mock_agent

            result = asyncio.run(run_agent(mock_page, "do something"))
            assert result["success"] is False
            assert "unexpected agent failure" in result["summary"]
            assert isinstance(result["steps"], list)


# ============================================================
# 3. run_agent Event Publishing Tests
# ============================================================

class TestRunAgentEventPublishing:
    """Test that run_agent publishes tool_called events."""

    def test_tool_called_event_published(self):
        from skiritai.events import Event, event_bus

        events: list[Event] = []

        async def capture(event: Event):
            if event.type == "tool_called":
                events.append(event)

        event_bus.subscribe(capture, event_types=["tool_called"])

        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()
        mock_page.url = "http://localhost"

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def stream(*args, **kwargs):
                msg = MagicMock()
                msg.tool_calls = [
                    {"name": "navigate", "args": {"url": "http://x.com"}},
                    {"name": "click", "args": {"selector": "#btn"}},
                ]
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = stream
            mock_build.return_value = mock_agent

            try:
                result = asyncio.run(
                    run_agent(mock_page, "do it", execution_id="e1")
                )
            finally:
                event_bus.unsubscribe(capture)

        assert len(events) == 2
        assert events[0].data["tool_name"] == "navigate"
        assert events[0].data["tool_args"] == {"url": "http://x.com"}
        assert events[1].data["tool_name"] == "click"
        assert events[1].data["tool_args"] == {"selector": "#btn"}
        assert events[0].execution_id == "e1"

    def test_no_tool_called_for_content_only_message(self):
        from skiritai.events import Event, event_bus

        events: list[Event] = []

        async def capture(event: Event):
            if event.type == "tool_called":
                events.append(event)

        event_bus.subscribe(capture, event_types=["tool_called"])

        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def stream(*args, **kwargs):
                # Message with only content, no tool_calls
                msg = MagicMock()
                msg.content = "Task completed"
                # hasattr check will fail, no tool_calls
                del msg.tool_calls  # simulate no tool_calls attribute
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = stream
            mock_build.return_value = mock_agent

            try:
                asyncio.run(run_agent(mock_page, "do it", execution_id="e2"))
            finally:
                event_bus.unsubscribe(capture)

        assert len(events) == 0

    def test_on_log_callback_called(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()
        log_messages: list[str] = []

        async def on_log(msg: str):
            log_messages.append(msg)

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            async def stream(*args, **kwargs):
                msg = MagicMock()
                msg.tool_calls = [
                    {"name": "click", "args": {"selector": "#submit"}}
                ]
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = stream
            mock_build.return_value = mock_agent

            asyncio.run(
                run_agent(mock_page, "click button", on_log=on_log)
            )

        assert len(log_messages) >= 1
        assert "click" in log_messages[0]


# ============================================================
# 4. run_agent Recursion Limit Tests
# ============================================================

class TestRunAgentConfig:
    """Test run_agent configuration parameters."""

    def test_recursion_limit_is_set(self):
        from skiritai.core.agent_loop import run_agent

        mock_page = MagicMock()

        with patch("skiritai.core.agent_loop.build_agent") as mock_build:
            mock_agent = MagicMock()

            configs_received = []

            async def stream(_input, **kwargs):
                configs_received.append(kwargs.get("config", {}))
                msg = MagicMock()
                msg.content = "done"
                msg.tool_calls = None
                yield {"agent": {"messages": [msg]}}

            mock_agent.astream = stream
            mock_build.return_value = mock_agent

            asyncio.run(run_agent(mock_page, "test"))
            assert configs_received[0].get("recursion_limit") == 20


# ============================================================
# 5. SYSTEM_PROMPT and PERCEPTION_TOOLS Tests
# ============================================================

class TestAgentLoopConstants:
    """Test agent loop constants and configuration."""

    def test_perception_tools_are_read_only(self):
        from skiritai.core.agent_loop import PERCEPTION_TOOLS

        assert "page_perceive" in PERCEPTION_TOOLS
        assert "find_element" in PERCEPTION_TOOLS
        assert "analyze_page" in PERCEPTION_TOOLS

    def test_system_prompt_is_chinese(self):
        from skiritai.core.agent_loop import SYSTEM_PROMPT

        assert "浏览器自动化测试 Agent" in SYSTEM_PROMPT
        assert "analyze_page" in SYSTEM_PROMPT
        assert "get_page_info" in SYSTEM_PROMPT


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
