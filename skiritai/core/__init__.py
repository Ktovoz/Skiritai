"""Skiritai core engine — AI-driven browser test automation.

Public API:
    Case management:  BaseCase, step, step_mode, AIContext, ActionMode
    Execution:        run_agent, register_all_tools, PERCEPTION_TOOLS
    Functional API:   flow (no-subclass context manager)
    YAML cases:       run_yaml_case, load_yaml_case, list_yaml_cases
    State:            CaseContext, CasePhase, GlobalStore
    Browser:          browser (module), perception (module)
    Infrastructure:   event_bus, ToolRegistry
    Script generation: generate_replay_script
"""
from skiritai.core.agent_loop import PERCEPTION_TOOLS, register_all_tools
from skiritai.core.ai_context import AIContext, ActionMode
from skiritai.core.base_case import BaseCase, step, step_mode, on_failure, FailurePolicy, StepResult
from skiritai.core.case_context import CaseContext, CasePhase, GlobalStore
from skiritai.core.flow import flow, FlowAI
from skiritai.core.runner import run_case, discover_case_class, list_cases
from skiritai.core.script_generator import generate_replay_script
from skiritai.core.tool_registry import ToolRegistry
from skiritai.core.yaml_runner import run_yaml_case, load_yaml_case, list_yaml_cases

__all__ = [
    # Case framework
    "BaseCase",
    "step",
    "step_mode",
    "on_failure",
    "FailurePolicy",
    "StepResult",
    "AIContext",
    "ActionMode",
    # Agent
    "register_all_tools",
    "PERCEPTION_TOOLS",
    # Functional API
    "flow",
    "FlowAI",
    # State
    "CaseContext",
    "CasePhase",
    "GlobalStore",
    # Tools
    "ToolRegistry",
    # Script generation
    "generate_replay_script",
    # Runner
    "run_case",
    "discover_case_class",
    "list_cases",
    # YAML cases
    "run_yaml_case",
    "load_yaml_case",
    "list_yaml_cases",
]
