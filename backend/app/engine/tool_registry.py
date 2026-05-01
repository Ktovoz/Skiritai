"""Tool registry with self-registration pattern."""
from __future__ import annotations

from langchain_core.tools import Tool, tool as lc_tool


class ToolRegistry:
    """Singleton registry for LangChain tools with auto-discovery."""

    _instance: ToolRegistry | None = None
    _tools: dict[str, Tool] = {}

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
        return cls._instance

    def register(self, tool: Tool) -> Tool:
        """Register a LangChain tool. Returns the tool unchanged (passthrough)."""
        self._tools[tool.name] = tool
        return tool

    def get_all(self) -> list[Tool]:
        """Return all registered tools as a list."""
        return list(self._tools.values())

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def clear(self) -> None:
        """Clear all registered tools. Useful for testing."""
        self._tools.clear()


_registry = ToolRegistry()


def register_tool(func=None, **kwargs):
    """Decorator that combines @tool (LangChain) and auto-registration.

    Usage:
        @register_tool
        async def my_tool(param: str) -> str:
            ...

        @register_tool(name="custom_name")
        async def my_tool(param: str) -> str:
            ...
    """
    def decorator(fn):
        lc_tool_obj = lc_tool(fn, **kwargs)
        return _registry.register(lc_tool_obj)

    if func is not None:
        return decorator(func)
    return decorator
