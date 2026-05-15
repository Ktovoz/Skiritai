"""Skiritai — AI-driven browser test automation framework.

Usage — run a case from a directory (CLI / runner):
    from skiritai import run_case
    from pathlib import Path
    import asyncio

    report = asyncio.run(run_case(Path("cases/my_test")))

Usage — run a case class directly (library):
    from skiritai import BaseCase, step, register_all_tools
    import asyncio

    class MyCase(BaseCase):
        @step
        async def open_page(self, ai):
            await ai.action("打开首页")

    register_all_tools()
    case = MyCase(case_dir=Path("cases/my_test"))
    report = asyncio.run(case.run())

Usage — functional API (no subclass):
    from skiritai import flow

    async with flow() as ai:
        await ai.action("打开首页")
        await ai.screenshot("homepage")

Usage — YAML case:
    from skiritai import run_yaml_case
    report = asyncio.run(run_yaml_case(Path("cases/my_yaml_case")))
"""
from skiritai.core import (
    BaseCase,
    step,
    step_mode,
    on_failure,
    FailurePolicy,
    AIContext,
    ActionMode,
    flow,
    FlowAI,
    run_case,
    discover_case_class,
    list_cases,
    run_yaml_case,
    load_yaml_case,
    list_yaml_cases,
)
from skiritai.events import Event, EventBus, event_bus
from skiritai.llm import create_llm, load_env

__version__ = "0.0.10a1"

__all__ = [
    # Case framework
    "BaseCase",
    "step",
    "step_mode",
    "on_failure",
    "FailurePolicy",
    "AIContext",
    "ActionMode",
    # Functional API
    "flow",
    "FlowAI",
    # Events
    "Event",
    "EventBus",
    "event_bus",
    # LLM factory
    "create_llm",
    "load_env",
    # Runner
    "run_case",
    "discover_case_class",
    "list_cases",
    # YAML cases
    "run_yaml_case",
    "load_yaml_case",
    "list_yaml_cases",
]
