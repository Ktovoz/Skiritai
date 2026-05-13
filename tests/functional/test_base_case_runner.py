"""Functional tests for BaseCase and PyCaseRunner — no browser/LLM required."""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBaseCase:
    """Test step discovery, decorator, and lifecycle."""

    def test_step_discovery_auto_detects_all_public_methods(self):
        """Public methods are auto-detected as steps (no @step or 'ai' param needed)."""
        from skiritai.core.base_case import BaseCase, step_mode

        class MyCase(BaseCase):
            async def setup(self):
                pass

            async def teardown(self):
                pass

            async def open_page(self):
                """Open the home page — auto-detected."""

            @step_mode("explore")
            async def search(self):
                """Search for keywords."""
                pass

            def helper_method(self):
                """Public helpers are also detected — use _prefix for non-steps."""
                pass

        case = MyCase()
        steps = case.get_step_methods()

        assert "open_page" in steps
        assert "search" in steps
        assert "helper_method" in steps  # all public methods are steps
        assert "setup" not in steps
        assert "teardown" not in steps
        assert "get_step_methods" not in steps

    def test_step_mode_decorator_sets_mode(self):
        from skiritai.core.base_case import BaseCase, step_mode

        class MyCase(BaseCase):
            @step_mode("explore")
            async def my_step(self):
                pass

        method = getattr(MyCase, "my_step")
        assert getattr(method, "_step_mode", "auto") == "explore"

    def test_default_mode_is_auto(self):
        from skiritai.core.base_case import BaseCase

        class MyCase(BaseCase):
            async def my_step(self):
                pass

        method = getattr(MyCase, "my_step")
        assert getattr(method, "_step_mode", "auto") == "auto"

    def test_results_dir_stored(self):
        from skiritai.core.base_case import BaseCase

        results_dir = Path("/tmp/fake_results")
        case = BaseCase(case_dir=Path("/tmp"), results_dir=results_dir)
        assert case._results_dir == results_dir

    def test_results_dir_defaults_to_none(self):
        from skiritai.core.base_case import BaseCase

        case = BaseCase()
        assert case._results_dir is None


class TestPyCaseRunner:
    """Test case discovery and listing."""

    def test_discover_case_class(self):
        from skiritai.core.runner import discover_case_class

        case_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "beginner" / "baidu_search" / "01_basecase"
        cls = discover_case_class(case_dir)
        assert cls.__name__ == "BaiduSearchCase"

    def test_list_cases_returns_all(self):
        from skiritai.core.runner import list_cases

        cases_root = Path(__file__).resolve().parent.parent.parent / "examples"
        cases = list_cases(cases_root)
        assert len(cases) >= 6  # 01_basecase, 02_flow, 03_yaml, etc.

        case_ids = [c["id"] for c in cases]
        assert "baidu_search__01_basecase" in case_ids
        # check that nested directory names show up as case IDs
        found_beginner = any("beginner" in c.get("dir", "") for c in cases)
        assert found_beginner, "cases should include beginner examples"

    def test_list_cases_structure(self):
        from skiritai.core.runner import list_cases

        cases_root = Path(__file__).resolve().parent.parent.parent / "examples"
        cases = list_cases(cases_root)

        for c in cases:
            assert "id" in c
            assert "name" in c
            assert "dir" in c
            assert "steps" in c
            assert isinstance(c["steps"], list)

    def test_run_case_accepts_results_dir(self):
        from skiritai.core.base_case import BaseCase
        from skiritai.core.runner import run_case

        with tempfile.TemporaryDirectory() as tmpdir:
            class FakeCase(BaseCase):
                pass

            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(return_value={
                "case_name": "FakeCase",
                "status": "completed",
                "total_steps": 1,
                "success_count": 1,
                "failed_count": 0,
                "steps": [],
            })

            with patch(
                    "skiritai.core.runner.discover_case_class",
                    return_value=FakeCase,
            ):
                with patch.object(FakeCase, "__new__", return_value=mock_instance):
                    results_dir = Path(tmpdir) / "results"
                    report = asyncio.run(
                        run_case(
                            case_dir=Path("/fake"),
                            results_dir=results_dir,
                        )
                    )
                    assert report["status"] == "completed"


class TestBrowserConfig:
    """Test browser launch args configuration."""

    def test_default_is_not_headless(self):
        old_sk = os.environ.pop("SKIRITAI_HEADLESS", None)
        old_h = os.environ.pop("HEADLESS", None)
        try:
            from skiritai.core.browser import get_launch_args

            args = get_launch_args()
            assert args["headless"] is False
        finally:
            if old_sk:
                os.environ["SKIRITAI_HEADLESS"] = old_sk
            if old_h:
                os.environ["HEADLESS"] = old_h

    def test_headless_true_via_env(self):
        old = os.environ.get("SKIRITAI_HEADLESS")
        os.environ["SKIRITAI_HEADLESS"] = "true"
        try:
            from skiritai.core.browser import get_launch_args

            args = get_launch_args()
            assert args["headless"] is True
        finally:
            if old is None:
                os.environ.pop("SKIRITAI_HEADLESS", None)
            else:
                os.environ["SKIRITAI_HEADLESS"] = old

    def test_headless_accepts_1_and_yes(self):
        old = os.environ.get("SKIRITAI_HEADLESS")
        for val in ("1", "yes", "true"):
            os.environ["SKIRITAI_HEADLESS"] = val
            from skiritai.core.browser import get_launch_args
            assert get_launch_args()["headless"] is True, f"HEADLESS={val}"
        if old is None:
            os.environ.pop("SKIRITAI_HEADLESS", None)
        else:
            os.environ["SKIRITAI_HEADLESS"] = old

    def test_chrome_path_only_when_set(self):
        old = os.environ.pop("SKIRITAI_CHROME_PATH", None)
        old2 = os.environ.pop("CHROME_PATH", None)
        try:
            from skiritai.core.browser import get_launch_args

            args = get_launch_args()
            assert "executable_path" not in args
        finally:
            if old:
                os.environ["SKIRITAI_CHROME_PATH"] = old
            if old2:
                os.environ["CHROME_PATH"] = old2

    def test_headless_per_case_override(self):
        """Per-case headless=True overrides env var."""
        old = os.environ.get("SKIRITAI_HEADLESS")
        os.environ["SKIRITAI_HEADLESS"] = "false"  # env says headful
        try:
            from skiritai.core.browser import get_launch_args

            args = get_launch_args(headless=True)
            assert args["headless"] is True  # per-case wins
        finally:
            if old is None:
                os.environ.pop("SKIRITAI_HEADLESS", None)
            else:
                os.environ["SKIRITAI_HEADLESS"] = old


class TestLoggerConfig:
    """Test logger configuration."""

    def test_log_level_defaults_to_info(self):
        old = os.environ.pop("LOG_LEVEL", None)
        try:
            import skiritai.logger
            importlib.reload(skiritai.logger)
            assert skiritai.logger.LOG_LEVEL == "INFO"
        finally:
            if old:
                os.environ["LOG_LEVEL"] = old
            importlib.reload(skiritai.logger)

    def test_log_level_from_env(self):
        old = os.environ.get("LOG_LEVEL")
        os.environ["LOG_LEVEL"] = "WARNING"
        try:
            import skiritai.logger
            importlib.reload(skiritai.logger)
            assert skiritai.logger.LOG_LEVEL == "WARNING"
        finally:
            if old is None:
                os.environ.pop("LOG_LEVEL", None)
            else:
                os.environ["LOG_LEVEL"] = old
            importlib.reload(skiritai.logger)


class TestToolRegistry:
    """Test tool self-registration."""

    def test_tools_are_registered(self):
        from skiritai.core.tool_registry import ToolRegistry

        registry = ToolRegistry()
        tools = registry.get_all()

        tool_names = [t.name for t in tools]
        assert len(tools) >= 14  # 14+ tools including analyze_page
        assert "navigate" in tool_names
        assert "click" in tool_names
        assert "fill" in tool_names
        assert "get_page_info" in tool_names
        assert "screenshot" in tool_names

    def test_tool_registry_is_singleton(self):
        from skiritai.core.tool_registry import ToolRegistry

        r1 = ToolRegistry()
        r2 = ToolRegistry()
        assert r1 is r2


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", pytest.__file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
