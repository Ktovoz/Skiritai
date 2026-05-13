"""Case management, execution, and script API."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from skiritai.core.execution_manager import cancel_execution, register_execution, unregister_execution
from skiritai.core.runner import discover_case_class, list_cases, run_case
from skiritai.events import event_bus
from skiritai.logger import logger
from skiritai.web.ws_manager import ws_manager

router = APIRouter(prefix="/api/cases", tags=["cases"])

# Configurable cases root — set via create_app() or SKIRITAI_CASES_ROOT
CASES_ROOT = Path.cwd() / "examples"

# Case index cache: {case_id: Path} — rebuilt when set_cases_root() is called
_case_index: dict[str, Path] | None = None

# LLM provider — set via create_app(), shared by all API requests
_llm_config = None


def _build_case_index() -> dict[str, Path]:
    """Scan CASES_ROOT and build a {case_id: directory_path} index.

    Uses leaf directory names as IDs. When multiple directories share the same
    leaf name, disambiguates by prefixing with the parent directory name
    separated by ``__`` (e.g. ``baidu_search__01_basecase``).
    """
    from collections import Counter

    index: dict[str, Path] = {}
    if not CASES_ROOT.exists():
        return index

    all_dirs = [case_py.parent for case_py in CASES_ROOT.rglob("case.py")]
    name_counts = Counter(d.name for d in all_dirs)

    for d in all_dirs:
        if name_counts[d.name] > 1:
            case_id = f"{d.parent.name}__{d.name}"
        else:
            case_id = d.name
        index[case_id] = d
    return index


def set_cases_root(root: Path) -> None:
    """Set the root directory for case discovery. Called by create_app()."""
    global CASES_ROOT, _case_index
    CASES_ROOT = root.resolve()
    _case_index = _build_case_index()
    logger.info(f"[API] Cases root: {CASES_ROOT} ({len(_case_index)} cases indexed)")


def set_llm(llm) -> None:
    """Set the LLM provider for the web server. Called by create_app()."""
    global _llm_config
    _llm_config = llm


def _find_case_dir(case_id: str) -> Path | None:
    """Find a case directory by its leaf name (uses cached index)."""
    global _case_index
    if _case_index is None:
        _case_index = _build_case_index()
    return _case_index.get(case_id)


def _get_case_dir_or_404(case_id: str) -> Path:
    """Find a case directory or raise 404."""
    case_dir = _find_case_dir(case_id)
    if not case_dir:
        raise HTTPException(status_code=404, detail="Case not found")
    return case_dir


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
    case_dir = _find_case_dir(case_id)
    if case_dir is None:
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
                "description": _get_step_description(case_class, step),
            }
            for step in steps
        ],
    }


def _get_step_description(case_class: type, step_name: str) -> str:
    """Extract the first line of a step method's docstring as description."""
    method = getattr(case_class, step_name, None)
    if method and method.__doc__:
        return method.__doc__.strip().split("\n")[0]
    return ""


# --- Execution APIs ---


@router.post("/{case_id}/run")
async def api_run_case(case_id: str):
    """Execute a case."""
    case_dir = _find_case_dir(case_id)
    if case_dir is None:
        raise HTTPException(status_code=404, detail="Case not found")

    # Cancel any previous execution for this case
    await cancel_execution(case_id)

    async def _run():
        async def _ws_bridge(event):
            await ws_manager.handle_event(event)

        event_bus.subscribe(_ws_bridge)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = case_dir / "test_results" / timestamp
        try:
            report = await run_case(case_dir, execution_id=case_id, results_dir=results_dir, llm=_llm_config)
            # Save result to disk (API path — distinct from CLI path which uses BaseCase._save_report)
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
            )
            logger.info(f"[API] Case {case_id} completed, results saved to {results_dir}")
        except asyncio.CancelledError:
            logger.info(f"[API] Case {case_id} execution cancelled")
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "report.json").write_text(
                json.dumps({
                    "case_name": case_id,
                    "status": "cancelled",
                    "total_steps": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "steps": [],
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"[CaseRunner] Case {case_id} failed: {e}")
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "report.json").write_text(
                json.dumps({
                    "case_name": case_id,
                    "status": "error",
                    "total_steps": 0,
                    "success_count": 0,
                    "failed_count": 1,
                    "steps": [{"step_id": "__execution__", "status": "failed", "error": str(e)}],
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        finally:
            event_bus.unsubscribe(_ws_bridge)
            await unregister_execution(case_id)

    task = asyncio.create_task(_run())
    await register_execution(case_id, task)
    logger.info(f"[API] Case execution started: {case_id}")

    return {"case_id": case_id, "status": "started", "message": "Execution started"}


@router.post("/{case_id}/stop")
async def api_stop_case(case_id: str):
    """Stop a running case execution."""
    case_dir = _find_case_dir(case_id)
    if case_dir is None:
        raise HTTPException(status_code=404, detail="Case not found")

    cancelled = await cancel_execution(case_id)
    if cancelled:
        return {"case_id": case_id, "status": "cancelled", "message": "Execution cancelled"}
    else:
        return {"case_id": case_id, "status": "not_found", "message": "No running execution found"}


# --- Script APIs ---

@router.get("/{case_id}/scripts")
async def api_list_scripts(case_id: str):
    """List all scripts for a case."""
    scripts_dir = _get_case_dir_or_404(case_id) / "scripts"
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
    script_path = _get_case_dir_or_404(case_id) / "scripts" / f"{step_id}.py"
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
    """Update script content and recompute integrity hash."""
    script_path = _get_case_dir_or_404(case_id) / "scripts" / f"{step_id}.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")

    script_path.write_text(body.content, encoding="utf-8")
    # Recompute hash so _verify_script() won't reject the updated script
    from skiritai.core.ai_context import _save_script_hash
    _save_script_hash(script_path, body.content)
    return {"step_id": step_id, "content": body.content}


@router.post("/{case_id}/scripts/{step_id}/solidify")
async def api_solidify_script(case_id: str, step_id: str):
    """Solidify a script so it persists for replay mode.

    This confirms the script exists and is ready for replay.
    """
    scripts_dir = _get_case_dir_or_404(case_id) / "scripts"
    script_path = scripts_dir / f"{step_id}.py"

    # Create scripts dir if it doesn't exist
    scripts_dir.mkdir(parents=True, exist_ok=True)

    if not script_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Script not found. Run the case in explore mode first to generate the script.",
        )

    # Mark as solidified by creating a marker file
    marker_path = scripts_dir / f".{step_id}.solidified"
    marker_path.touch()

    return {
        "step_id": step_id,
        "status": "solidified",
        "message": "Script is solidified and ready for replay",
    }


# --- Result APIs ---

@router.get("/{case_id}/results")
async def api_list_results(case_id: str):
    """List all execution results for a case."""
    case_dir = _get_case_dir_or_404(case_id)
    results_dir = case_dir / "test_results"
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
    results_dir = _get_case_dir_or_404(case_id) / "test_results" / timestamp
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


@router.get("/{case_id}/results/{timestamp}/screenshots/{filename}")
async def api_get_screenshot(case_id: str, timestamp: str, filename: str):
    """Serve a screenshot file."""
    import re
    if not re.match(r'^[a-zA-Z0-9_. -]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    screenshot_path = _get_case_dir_or_404(case_id) / "test_results" / timestamp / "screenshots" / filename
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(screenshot_path, media_type="image/png")
