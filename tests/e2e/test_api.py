"""E2E tests — REST API lifecycle with real browser."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

os.environ["SKIRITAI_HEADLESS"] = "true"

from skiritai.core.runner import run_case


class TestAPILifecycle:
    """Test the REST API with real case execution."""

    @pytest.fixture(autouse=True)
    def setup_client(self, multi_step_case):
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app
        from skiritai.core.execution_manager import _executions

        _executions.clear()
        self.case_dir, self.case_id, self.url = multi_step_case
        self.parent_dir = self.case_dir.parent

        # Pass cases_root to create_app so it configures the router correctly
        self.client = TestClient(create_app(cases_root=self.parent_dir))
        yield

    def test_api_list_cases(self):
        resp = self.client.get("/api/cases")
        assert resp.status_code == 200
        cases = resp.json()
        case_ids = [c["id"] for c in cases]
        assert self.case_id in case_ids

    def test_api_get_case_detail(self):
        resp = self.client.get(f"/api/cases/{self.case_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == self.case_id
        assert "steps" in detail
        assert len(detail["steps"]) == 2

        for step in detail["steps"]:
            assert "id" in step
            assert "name" in step
            assert "mode" in step
            assert "description" in step

    def test_api_list_scripts(self):
        resp = self.client.get(f"/api/cases/{self.case_id}/scripts")
        assert resp.status_code == 200
        scripts = resp.json()
        assert len(scripts) == 2

        for script in scripts:
            assert "step_id" in script
            assert "path" in script
            assert "content" in script
            assert "async def run" in script["content"]

    def test_api_run_and_query_results(self):
        report = asyncio.run(run_case(
            case_dir=self.case_dir,
            execution_id=self.case_id,
        ))
        assert report["status"] == "completed"
        assert report["success_count"] == 2

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_dir = self.case_dir / "results" / timestamp
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        resp = self.client.get(f"/api/cases/{self.case_id}/results")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1

        latest = results[0]
        assert latest["report"]["status"] == "completed"
        assert latest["report"]["success_count"] == 2

        shutil.rmtree(results_dir, ignore_errors=True)

    def test_api_stop_when_no_execution(self):
        resp = self.client.post(f"/api/cases/{self.case_id}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_found"

    def test_api_nonexistent_case_returns_404(self):
        resp = self.client.get("/api/cases/does_not_exist")
        assert resp.status_code == 404


class TestResultsPersistence:
    """Verify reports and screenshots are saved correctly."""

    @pytest.mark.asyncio
    async def test_report_json_saved(self, simple_case):
        case_dir, url = simple_case
        results_dir = case_dir / "results" / "persist_test"

        report = await run_case(
            case_dir=case_dir,
            execution_id="persist_test",
            results_dir=results_dir,
        )

        assert report["status"] == "completed"

        json_str = json.dumps(report, ensure_ascii=False)
        loaded = json.loads(json_str)
        assert loaded == report

    @pytest.mark.asyncio
    async def test_report_has_all_fields(self, simple_case):
        case_dir, url = simple_case

        report = await run_case(case_dir=case_dir, execution_id="fields_test")

        required_keys = {"case_name", "status", "total_steps", "success_count", "failed_count", "steps"}
        assert required_keys.issubset(report.keys())

        for step in report["steps"]:
            step_keys = {"step_id", "status", "mode", "summary"}
            assert step_keys.issubset(step.keys())

    @pytest.mark.asyncio
    async def test_screenshot_saved_on_failure(self, case_url):
        url, _ = case_url
        tmpdir = tempfile.mkdtemp(prefix="e2e_screenshot_")
        case_dir = Path(tmpdir) / "screenshot_case"
        case_dir.mkdir()
        results_dir = case_dir / "results" / "screenshot_test"

        (case_dir / "case.py").write_text(
            "from skiritai.core.base_case import BaseCase\n"
            "\n"
            "class ScreenshotCase(BaseCase):\n"
            "    async def setup(self):\n"
            "        await self.launch_browser()\n"
            "    async def teardown(self):\n"
            "        await self.close_browser()\n"
            "    async def crash_step(self, ai):\n"
            '        await ai.action("navigate first")\n'
            '        raise RuntimeError("intentional crash for screenshot")\n',
            encoding="utf-8",
        )

        scripts_dir = case_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "crash_step").with_suffix(".py").write_text(
            "async def run(page, context):\n"
            f'    await page.goto("{url}")\n'
            "    await page.wait_for_load_state('networkidle')\n",
            encoding="utf-8",
        )

        report = await run_case(
            case_dir=case_dir,
            execution_id="screenshot_test",
            results_dir=results_dir,
        )

        assert report["status"] == "failed"

        screenshot_path = results_dir / "screenshots" / "crash_step.png"
        assert screenshot_path.exists(), f"Screenshot not found at {screenshot_path}"
        assert screenshot_path.stat().st_size > 0

        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
        env={**os.environ, "HEADLESS": "true"},
    )
    sys.exit(result.returncode)
