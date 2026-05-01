"""Case management, execution, and script API."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.engine.py_case_runner import discover_case_class, list_cases, run_case
from app.engine.ws_manager import ws_manager
from app.logger import logger

router = APIRouter(prefix="/api/cases", tags=["cases"])

CASES_ROOT = Path(__file__).resolve().parent.parent.parent / "cases"


# --- Case APIs ---

@router.get("")
async def api_list_cases():
    """List all cases."""
    cases = list_cases(CASES_ROOT)
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "description": c.get("description", ""),
            "steps": len(c["steps"]),
            "case_dir": c["dir"],
        }
        for c in cases
    ]


@router.get("/{case_id}")
async def api_get_case(case_id: str):
    """Get case details with steps."""
    case_dir = CASES_ROOT / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail="Case not found")
    case_class = discover_case_class(case_dir)
    instance = case_class(case_dir=case_dir)
    steps = instance.get_step_methods()
    return {
        "id": case_id,
        "name": case_class.__name__,
        "description": case_class.__doc__ or "",
        "steps": [
            {
                "id": step,
                "name": step,
                "mode": "explore" if not (case_dir / "scripts" / f"{step}.py").exists() else "solidified",
                "description": "",
            }
            for step in steps
        ],
    }


# --- Execution APIs ---

class RunResponse(BaseModel):
    case_id: str
    status: str
    message: str


@router.post("/{case_id}/run")
async def api_run_case(case_id: str):
    """Execute a case."""
    case_dir = CASES_ROOT / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail="Case not found")

    async def _run():
        try:
            await run_case(case_dir)
        except Exception as e:
            logger.error(f"[CaseRunner] Case {case_id} failed: {e}")

    asyncio.create_task(_run())
    logger.info(f"[API] Case execution started: {case_id}")

    return {"case_id": case_id, "status": "started", "message": "Execution started"}


# --- Script APIs ---

@router.get("/{case_id}/scripts")
async def api_list_scripts(case_id: str):
    """List all scripts for a case."""
    scripts_dir = CASES_ROOT / case_id / "scripts"
    if not scripts_dir.exists():
        return []

    scripts = []
    for f in sorted(scripts_dir.glob("*.py")):
        step_id = f.stem
        scripts.append({
            "step_id": step_id,
            "path": str(f),
            "content": f.read_text(encoding="utf-8"),
        })
    return scripts


@router.get("/{case_id}/scripts/{step_id}")
async def api_get_script(case_id: str, step_id: str):
    """Get script content for a specific step."""
    script_path = CASES_ROOT / case_id / "scripts" / f"{step_id}.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")

    return {
        "step_id": step_id,
        "content": script_path.read_text(encoding="utf-8"),
    }


class ScriptUpdate(BaseModel):
    content: str


@router.put("/{case_id}/scripts/{step_id}")
async def api_update_script(case_id: str, step_id: str, body: ScriptUpdate):
    """Update script content."""
    script_path = CASES_ROOT / case_id / "scripts" / f"{step_id}.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")

    script_path.write_text(body.content, encoding="utf-8")
    return {"step_id": step_id, "content": body.content}


class SolidifyRequest(BaseModel):
    mode: str = "solidified"


@router.post("/{case_id}/scripts/{step_id}/solidify")
async def api_solidify_script(case_id: str, step_id: str):
    """Mark a step's script as solidified by updating case.yaml."""
    case_dir = CASES_ROOT / case_id
    case_file = case_dir / "case.yaml"
    if not case_file.exists():
        raise HTTPException(status_code=404, detail="Case not found")

    script_path = case_dir / "scripts" / f"{step_id}.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")

    import yaml
    with open(case_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for step in data.get("steps", []):
        if step["id"] == step_id:
            step["mode"] = "solidified"
            break
    else:
        raise HTTPException(status_code=404, detail="Step not found in case.yaml")

    with open(case_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    return {"step_id": step_id, "mode": "solidified"}


# --- Result APIs ---

@router.get("/{case_id}/results")
async def api_list_results(case_id: str):
    """List all execution results for a case."""
    results_dir = CASES_ROOT / case_id / "results"
    if not results_dir.exists():
        return []

    results = []
    for d in sorted(results_dir.iterdir(), reverse=True):
        if d.is_dir():
            report_path = d / "report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                results.append({"timestamp": d.name, "report": report})
    return results


@router.get("/{case_id}/results/{timestamp}")
async def api_get_result(case_id: str, timestamp: str):
    """Get a specific execution result."""
    results_dir = CASES_ROOT / case_id / "results" / timestamp
    if not results_dir.exists():
        raise HTTPException(status_code=404, detail="Result not found")

    report_path = results_dir / "report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    report = json.loads(report_path.read_text(encoding="utf-8"))

    # List screenshots
    screenshots_dir = results_dir / "screenshots"
    screenshots = []
    if screenshots_dir.exists():
        for f in sorted(screenshots_dir.glob("*.png")):
            screenshots.append(f.stem)

    return {"timestamp": timestamp, "report": report, "screenshots": screenshots}
