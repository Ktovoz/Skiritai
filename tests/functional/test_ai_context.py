"""Functional tests for AIContext — no browser/LLM required."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAIContext:
    """Test AIContext explore/replay/script generation logic."""

    def test_script_path_and_has_replay(self):
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="open_page")

            assert ctx.script_path == case_dir / "scripts" / "open_page.py"
            assert ctx.has_replay() is False

            # Create a script file
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text("async def run(page, ctx): pass")
            assert ctx.has_replay() is True

    def test_mode_auto_replays_when_script_exists(self):
        from skiritai.core.ai_context import AIContext
        from skiritai.core.ai_context import _compute_script_hash, SCRIPT_HASH_SUFFIX

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="step1")

            # Write a valid replay script
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            script_content = "async def run(page, context):\n    pass\n"
            ctx.script_path.write_text(script_content)
            # Write the integrity hash so _verify_script passes
            hash_path = Path(str(ctx.script_path) + SCRIPT_HASH_SUFFIX)
            hash_path.write_text(_compute_script_hash(script_content))

            result = asyncio.run(ctx.action("do something", mode="auto"))
            assert result["success"] is True
            assert result["steps"][0]["action"] == "replay"

    def test_mode_explore_always_explores(self):
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()

            mock_page = MagicMock()
            mock_page.url = "http://test.com"
            ctx = AIContext(page=mock_page, case_dir=case_dir, step_id="step1")

            # Even if script exists, explore mode should overwrite
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            ctx.script_path.write_text("# existing")

            # Mock the agent run to avoid real LLM calls
            mock_result = {"success": True, "summary": "done", "steps": []}
            with patch.object(ctx, "_explore", AsyncMock(return_value=mock_result)):
                result = asyncio.run(ctx.action("do something", mode="explore"))
                assert result is mock_result

    def test_mode_replay_raises_without_script(self):
        from skiritai.core.ai_context import AIContext

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="step1")

            with pytest.raises(FileNotFoundError):
                asyncio.run(ctx.action("do something", mode="replay"))

    def test_generate_script_simple_actions(self):
        from skiritai.core.script_generator import generate_replay_script

        agent_steps = [
            {"action": "navigate", "args": {"url": "https://example.com"}},
            {"action": "click", "args": {"selector": "#btn"}},
            {"action": "fill", "args": {"selector": "#input", "text": "hello"}},
        ]

        script = generate_replay_script("test", agent_steps)
        assert "async def run(page, context):" in script
        assert 'await page.goto("https://example.com")' in script
        assert 'await page.click("#btn")' in script
        assert 'await page.fill("#input", "hello")' in script

    def test_generate_script_empty_steps_produces_pass(self):
        from skiritai.core.script_generator import generate_replay_script

        script = generate_replay_script("test", [])
        assert "async def run(page, context):" in script
        assert "    pass" in script

    def test_generate_script_all_action_types(self):
        from skiritai.core.script_generator import generate_replay_script

        agent_steps = [
            {"action": "navigate", "args": {"url": "http://a.com"}},
            {"action": "click", "args": {"selector": "#b"}},
            {"action": "click_force", "args": {"selector": "#c"}},
            {"action": "fill", "args": {"selector": "#d", "text": "t"}},
            {"action": "type_text", "args": {"selector": "#e", "text": "x"}},
            {"action": "focus", "args": {"selector": "#f"}},
            {"action": "wait_for", "args": {"selector": "#g", "timeout": 3000}},
            {"action": "scroll", "args": {"direction": "down", "amount": 500}},
            {"action": "eval_js", "args": {"expression": "1+1"}},
            {"action": "select_option", "args": {"selector": "#h", "value": "v"}},
            {"action": "hover", "args": {"selector": "#i"}},
        ]

        script = generate_replay_script("test", agent_steps)
        assert 'await page.goto("http://a.com")' in script
        assert 'await page.click("#b")' in script
        assert 'await page.click("#c", force=True)' in script
        assert 'await page.fill("#d", "t")' in script
        assert 'await page.locator("#e").press_sequentially("x")' in script
        assert 'await page.locator("#f").focus()' in script
        assert 'await page.wait_for_selector("#g", timeout=3000)' in script
        assert "await page.mouse.wheel(0, 500)" in script
        assert 'await page.evaluate("1+1")' in script or "await page.evaluate('1+1')" in script
        assert 'await page.select_option("#h", "v")' in script
        assert 'await page.hover("#i")' in script

    def test_replay_script_with_error_returns_failure(self):
        from skiritai.core.ai_context import AIContext
        from skiritai.core.ai_context import _compute_script_hash, SCRIPT_HASH_SUFFIX

        with tempfile.TemporaryDirectory() as tmpdir:
            case_dir = Path(tmpdir) / "mycase"
            case_dir.mkdir()
            ctx = AIContext(page=MagicMock(), case_dir=case_dir, step_id="step1")

            # Write a script that raises
            ctx.scripts_dir.mkdir(parents=True, exist_ok=True)
            script_content = "async def run(page, context):\n    raise RuntimeError('test error')\n"
            ctx.script_path.write_text(script_content)
            # Write the integrity hash so _verify_script passes
            hash_path = Path(str(ctx.script_path) + SCRIPT_HASH_SUFFIX)
            hash_path.write_text(_compute_script_hash(script_content))

            result = asyncio.run(ctx._replay())
            assert result["success"] is False
            assert "test error" in result["summary"]
