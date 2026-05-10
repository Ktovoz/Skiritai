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
"""
from skiritai.core import (
    BaseCase,
    step,
    step_mode,
    on_failure,
    FailurePolicy,
    AIContext,
    ActionMode,
    run_case,
    discover_case_class,
    list_cases,
)
from skiritai.events import Event, EventBus, event_bus

__version__ = "0.1.0"

__all__ = [
    # Case framework
    "BaseCase",
    "step",
    "step_mode",
    "on_failure",
    "FailurePolicy",
    "AIContext",
    "ActionMode",
    # Events
    "Event",
    "EventBus",
    "event_bus",
    # Runner
    "run_case",
    "discover_case_class",
    "list_cases",
]
