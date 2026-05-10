"""Tool registry with self-registration pattern.

Supports both singleton (production) and isolated instances (testing).
"""
from __future__ import annotations

from langchain_core.tools import Tool, tool as lc_tool


class ToolRegistry:
    """Registry for LangChain tools with auto-discovery.

    By default behaves as a singleton (for production use).
    Call ``ToolRegistry.create_isolated()`` to get a fresh, independent
    instance for testing without polluting the global registry.
    """

    _instance: ToolRegistry | None = None

    def __new__(cls) -> ToolRegistry:
        """Return the singleton instance (backward compatible)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self) -> None:
        # Guard: __new__ creates _tools; avoid overwriting on repeated calls
        if not hasattr(self, "_tools"):
            self._tools: dict[str, Tool] = {}

    @classmethod
    def create_isolated(cls) -> ToolRegistry:
        """Create a new, isolated ToolRegistry instance (not the singleton).

        Use in tests to avoid cross-test pollution:

            registry = ToolRegistry.create_isolated()
            # register tools on registry without affecting the global one
        """
        instance = object.__new__(cls)
        instance._tools = {}  # type: ignore[attr-defined]
        return instance

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

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the singleton instance.

        **Only use in test teardown** — calling this in production code
        will cause tools to be re-registered on next access.
        """
        if cls._instance is not None:
            cls._instance._tools.clear()  # type: ignore[attr-defined]
            cls._instance = None


# Module-level default registry (singleton)
_registry = ToolRegistry()


def register_tool(func=None, **kwargs):
    """Decorator that combines @tool (LangChain) and auto-registration.

    Registers the tool on the module-level singleton registry.

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
