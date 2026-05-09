"""Skiritai engine — AI-driven browser test automation.

Public API:
    Case management:  BaseCase, step, step_mode, AIContext, ActionMode
    Execution:        run_agent, register_all_tools, PERCEPTION_TOOLS
    State:            CaseContext, CasePhase, GlobalStore
    Browser:          browser (module), perception (module)
    Infrastructure:   event_bus, ToolRegistry
    Script generation: generate_replay_script
"""
from app.engine.ai_context import AIContext, ActionMode
from app.engine.agent_loop import PERCEPTION_TOOLS, register_all_tools
from app.engine.base_case import BaseCase, step, step_mode
from app.engine.case_context import CaseContext, CasePhase, GlobalStore
from app.engine.event_bus import Event, EventBus, event_bus
from app.engine.script_generator import generate_replay_script
from app.engine.tool_registry import ToolRegistry

__all__ = [
    # Case framework
    "BaseCase",
    "step",
    "step_mode",
    "AIContext",
    "ActionMode",
    # Agent
    "register_all_tools",
    "PERCEPTION_TOOLS",
    # State
    "CaseContext",
    "CasePhase",
    "GlobalStore",
    # Events
    "Event",
    "EventBus",
    "event_bus",
    # Tools
    "ToolRegistry",
    # Script generation
    "generate_replay_script",
]
