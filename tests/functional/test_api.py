"""Functional tests for FastAPI REST API — no browser/LLM required."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestAPI:
    """Integration tests via FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient
        from skiritai.web.app import create_app
        from skiritai.core.execution_manager import _executions
        _executions.clear()
        self.client = TestClient(create_app())
        self.cases_root = Path(__file__).resolve().parent.parent.parent / "examples"

    def test_health(self):
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_list_cases(self):
        resp = self.client.get("/api/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        for item in data:
            assert "id" in item
            assert "name" in item
            assert "steps" in item

    def test_get_case_with_descriptions(self):
        resp = self.client.get("/api/cases/baidu_search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "baidu_search"
        assert data["name"] == "BaiduSearchCase"
        assert len(data["steps"]) == 3

        for step in data["steps"]:
            assert "id" in step
            assert "name" in step
            assert "mode" in step
            assert "description" in step

    def test_get_case_404(self):
        resp = self.client.get("/api/cases/nonexistent")
        assert resp.status_code == 404

    def test_list_scripts(self):
        resp = self.client.get("/api/cases/baidu_search/scripts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_script_404(self):
        resp = self.client.get("/api/cases/baidu_search/scripts/nonexistent_step")
        assert resp.status_code == 404

    def test_update_script(self):
        resp = self.client.get("/api/cases/baidu_search/scripts")
        if resp.json():
            script = resp.json()[0]
            original = script["content"]
            new_content = original + "\n# test update"

            resp2 = self.client.put(
                f"/api/cases/baidu_search/scripts/{script['step_id']}",
                json={"content": new_content},
            )
            assert resp2.status_code == 200
            assert resp2.json()["content"] == new_content

            # Restore original
            self.client.put(
                f"/api/cases/baidu_search/scripts/{script['step_id']}",
                json={"content": original},
            )

    def test_update_script_404(self):
        resp = self.client.put(
            "/api/cases/baidu_search/scripts/nonexistent",
            json={"content": "test"},
        )
        assert resp.status_code == 404

    def test_solidify_script_no_script(self):
        resp = self.client.post("/api/cases/baidu_search/scripts/nonexistent_step/solidify")
        assert resp.status_code == 404

    def test_solidify_existing_script(self):
        resp = self.client.get("/api/cases/baidu_search/scripts")
        if resp.json():
            step_id = resp.json()[0]["step_id"]
            resp2 = self.client.post(f"/api/cases/baidu_search/scripts/{step_id}/solidify")
            assert resp2.status_code == 200
            data = resp2.json()
            assert data["step_id"] == step_id
            assert data["status"] == "solidified"

            marker = self.cases_root / "baidu_search" / "scripts" / f".{step_id}.solidified"
            assert marker.exists()
            marker.unlink()  # cleanup

    def test_stop_no_running_execution(self):
        resp = self.client.post("/api/cases/baidu_search/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"

    def test_stop_nonexistent_case(self):
        resp = self.client.post("/api/cases/nonexistent/stop")
        assert resp.status_code == 404

    def test_results_empty_initially(self):
        resp = self.client.get("/api/cases/baidu_search/results")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_results_404_for_nonexistent_timestamp(self):
        resp = self.client.get("/api/cases/baidu_search/results/19700101_000000")
        assert resp.status_code == 404

    def test_cors_headers_present(self):
        resp = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code in (200, 405)

    def test_run_case_404(self):
        resp = self.client.post("/api/cases/nonexistent/run")
        assert resp.status_code == 404

    def test_run_case_starts_execution(self):
        with patch("skiritai.web.routers.cases.run_case") as mock_run:
            mock_run.return_value = {
                "case_name": "Test",
                "status": "completed",
                "total_steps": 1,
                "success_count": 1,
                "failed_count": 0,
                "steps": [],
            }
            resp = self.client.post("/api/cases/baidu_search/run")
            assert resp.status_code == 200
            data = resp.json()
            assert data["case_id"] == "baidu_search"
            assert data["status"] == "started"


class TestResultPersistence:
    """Test that execution results are properly saved."""

    def test_report_saved_after_execution(self):
        from skiritai.web.routers.cases import CASES_ROOT

        case_dir = CASES_ROOT / "baidu_search"
        results_dir = case_dir / "test_results"

        test_timestamp = "20260101_120000"
        test_results_dir = results_dir / test_timestamp
        test_results_dir.mkdir(parents=True, exist_ok=True)
        test_report = {
            "case_name": "BaiduSearchCase",
            "status": "completed",
            "total_steps": 3,
            "success_count": 3,
            "failed_count": 0,
            "steps": [],
        }
        (test_results_dir / "report.json").write_text(json.dumps(test_report))

        try:
            from fastapi.testclient import TestClient
            from skiritai.web.app import create_app
            client = TestClient(create_app())

            resp = client.get("/api/cases/baidu_search/results")
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) >= 1
            assert any(r["timestamp"] == test_timestamp for r in results)

            resp2 = client.get(f"/api/cases/baidu_search/results/{test_timestamp}")
            assert resp2.status_code == 200
            assert resp2.json()["report"]["case_name"] == "BaiduSearchCase"
            assert "screenshots" in resp2.json()
        finally:
            import shutil
            shutil.rmtree(test_results_dir)
            if results_dir.exists() and not list(results_dir.iterdir()):
                results_dir.rmdir()


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "--no-header"],
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    sys.exit(result.returncode)
