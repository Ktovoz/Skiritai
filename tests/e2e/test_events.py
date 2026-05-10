"""E2E tests — event sequencing with real browser."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

os.environ["SKIRITAI_HEADLESS"] = "true"

from skiritai.core.base_case import BaseCase
from skiritai.core.runner import run_case
from skiritai.events import Event, event_bus


class TestEventSequencing:
    """Verify event bus publishes events in correct order during real execution."""

    @pytest.mark.asyncio
    async def test_events_in_correct_order(self, simple_case):
        case_dir, url = simple_case
        events: list[str] = []

        async def collector(event: Event):
            events.append(event.type)

        event_bus.subscribe(collector)
        try:
            report = await run_case(case_dir=case_dir, execution_id="event_order_test")
        finally:
            event_bus.unsubscribe(collector)

        assert report["status"] == "completed"

        assert events[0] == "execution_started"
        assert "step_started" in events
        assert "step_completed" in events
        assert events[-1] == "execution_completed"

        first_started = events.index("step_started")
        first_completed = events.index("step_completed")
        assert first_started < first_completed

    @pytest.mark.asyncio
    async def test_events_contain_execution_id(self, simple_case):
        case_dir, url = simple_case
        captured_ids: list[str] = []

        async def collector(event: Event):
            captured_ids.append(event.execution_id)

        event_bus.subscribe(collector)
        try:
            await run_case(case_dir=case_dir, execution_id="id_check_test")
        finally:
            event_bus.unsubscribe(collector)

        assert len(captured_ids) >= 3
        assert all(eid == "id_check_test" for eid in captured_ids)

    @pytest.mark.asyncio
    async def test_step_failure_publishes_step_failed(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_fail_")
        case_dir = Path(tmpdir) / "fail_case"
        case_dir.mkdir()

        (case_dir / "case.py").write_text(
            "from skiritai.core.base_case import BaseCase\n"
            "\n"
            "class FailCase(BaseCase):\n"
            "    async def setup(self):\n"
            "        await self.launch_browser()\n"
            "    async def teardown(self):\n"
            "        await self.close_browser()\n"
            "    async def broken_step(self, ai):\n"
            '        await ai.action("this will fail")\n',
            encoding="utf-8",
        )

        scripts_dir = case_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "broken_step.py").write_text(
            "async def run(page, context):\n"
            "    raise RuntimeError('intentional E2E failure')\n",
            encoding="utf-8",
        )

        step_events: list[tuple[str, str]] = []

        async def collector(event: Event):
            if event.type in ("step_completed", "step_failed"):
                step_events.append((event.type, event.data.get("step_id")))

        event_bus.subscribe(collector)
        try:
            report = await run_case(case_dir=case_dir, execution_id="fail_test")
        finally:
            event_bus.unsubscribe(collector)
            shutil.rmtree(tmpdir, ignore_errors=True)

        assert len(step_events) == 1
        assert step_events[0][1] == "broken_step"


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
        env={**os.environ, "HEADLESS": "true"},
    )
    sys.exit(result.returncode)
