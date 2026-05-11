"""YAML case runner — define test steps in YAML, run with AI.

Usage (YAML file)::

    # case.yaml
    name: 百度搜索测试
    steps:
      - action: 打开百度首页 https://www.baidu.com
      - action: 在搜索框输入 Playwright 并搜索
      - verify: 搜索结果页面正常加载
      - screenshot: search_result

Run from CLI::

    skiritai run examples/baidu_yaml

Run from Python::

    from skiritai import run_yaml_case
    report = await run_yaml_case(Path("examples/baidu_yaml"))

Supported step types:
    - ``action``:   Natural language action → AI executes it
    - ``verify``:   Natural language assertion → AI verifies, non-blocking on failure
    - ``screenshot``: Capture screenshot with given name
    - ``analyze``:  Pre-analyze page DOM (injects context into next action)
    - ``page_info``: Get page title, URL, text summary

Optional YAML fields:
    - ``name``:       Case display name (default: directory name)
    - ``headless``:   Run browser headless (default: env or false)
    - ``max_steps``:  Max agent tool-call steps per action (default: 20)
    - ``url``:        Navigate to this URL before running steps
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from skiritai.core.browser import get_launch_args
from skiritai.core.case_context import CaseContext
from skiritai.events import Event, event_bus
from skiritai.logger import logger

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def _require_yaml() -> None:
    if yaml is None:
        raise ImportError(
            "PyYAML is required for YAML cases. Install with: pip install pyyaml"
        )


def load_yaml_case(case_dir: Path) -> dict:
    """Load and parse a YAML case definition.

    Looks for ``case.yaml`` or ``case.yml`` in the given directory.

    Returns:
        Parsed YAML dict with at least a ``steps`` key.
    """
    _require_yaml()

    yaml_file = None
    for name in ("case.yaml", "case.yml"):
        p = case_dir / name
        if p.is_file():
            yaml_file = p
            break

    if yaml_file is None:
        raise FileNotFoundError(f"No case.yaml/case.yml found in {case_dir}")

    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"YAML case must be a mapping, got {type(data).__name__}")

    if "steps" not in data:
        raise ValueError(f"YAML case must contain a 'steps' key ({yaml_file})")

    if not isinstance(data["steps"], list):
        raise ValueError(f"'steps' must be a list ({yaml_file})")

    return data


async def run_yaml_case(
    case_dir: Path,
    on_log: Any = None,
    execution_id: str | None = None,
    results_dir: Path | None = None,
) -> dict:
    """Run a YAML-defined test case.

    Args:
        case_dir: Directory containing ``case.yaml``.
        on_log: Optional callback for real-time log streaming.
        execution_id: Execution identifier for events.
        results_dir: Directory for saving results.

    Returns:
        Report dict with case_name, status, steps, etc.
    """
    from playwright.async_api import async_playwright

    from skiritai.core.agent_loop import register_all_tools
    register_all_tools()

    definition = load_yaml_case(case_dir)
    case_name = definition.get("name", case_dir.name)
    headless = definition.get("headless")
    max_steps = definition.get("max_steps", 20)
    start_url = definition.get("url", "")
    steps = definition["steps"]

    eid = execution_id or case_dir.name
    rd = results_dir or case_dir

    # --- Browser lifecycle ---
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(**get_launch_args(headless))
    context = await browser.new_context()
    page = await context.new_page()

    ctx = CaseContext(case_dir=case_dir, execution_id=eid)
    ctx.browser.mode = "standard"
    ctx.browser.started_at = time.time()

    logger.info(f"[YamlRunner] {case_name} — {len(steps)} steps")

    await event_bus.publish(Event(
        type="execution_started",
        execution_id=eid,
        data={"case_name": case_name, "source": "yaml"},
    ))

    # Navigate to start URL if specified
    if start_url:
        await page.goto(start_url)
        await page.wait_for_load_state("networkidle")
        logger.info(f"[YamlRunner] Navigated to {start_url}")

    # --- Execute steps ---
    results: list[dict] = []
    success_count = 0
    aborted = False

    for i, step_def in enumerate(steps):
        step_name = step_def.get("name", f"step_{i + 1}")

        # Determine step type and argument
        step_type = None
        step_arg = None
        for key in ("action", "verify", "screenshot", "analyze", "page_info"):
            if key in step_def:
                step_type = key
                step_arg = step_def[key]
                break

        if step_type is None:
            logger.warning(f"[YamlRunner] Unknown step definition at index {i}: {step_def}")
            continue

        await event_bus.publish(Event(
            type="step_started",
            execution_id=eid,
            data={"step_id": step_name, "step_type": step_type},
        ))

        logger.info(f"[YamlRunner] {step_name} ({step_type}): {step_arg}")

        # Create a fresh AIContext for each step
        from skiritai.core.ai_context import AIContext
        ai = AIContext(
            page=page,
            case_dir=case_dir,
            step_id=step_name,
            on_log=on_log,
            default_mode="auto",
            execution_id=eid,
            max_steps=max_steps,
        )
        ai._step_started_at = time.time()

        entry: dict[str, Any] = {
            "step_id": step_name,
            "type": step_type,
        }

        try:
            if step_type == "action":
                result = await ai.action(str(step_arg))
                ai._step_elapsed = time.time() - ai._step_started_at
                ok = result.get("success", False)
                entry.update({
                    "status": "success" if ok else "failed",
                    "mode": "replay" if ai.has_replay() else "explore",
                    "summary": result.get("summary", ""),
                    "elapsed": round(ai._step_elapsed, 2),
                })

            elif step_type == "verify":
                result = await ai.verify(str(step_arg))
                ai._step_elapsed = time.time() - ai._step_started_at
                passed = result.get("passed", False)
                entry.update({
                    "status": "passed" if passed else "failed",
                    "assertion": str(step_arg),
                    "reason": result.get("reason", ""),
                    "elapsed": round(ai._step_elapsed, 2),
                })

            elif step_type == "screenshot":
                path = await ai.screenshot(str(step_arg))
                ai._step_elapsed = time.time() - ai._step_started_at
                entry.update({
                    "status": "success",
                    "screenshot": path,
                    "elapsed": round(ai._step_elapsed, 2),
                })

            elif step_type == "analyze":
                result = await ai.analyze_page()
                ai._step_elapsed = time.time() - ai._step_started_at
                entry.update({
                    "status": "success",
                    "elapsed": round(ai._step_elapsed, 2),
                })

            elif step_type == "page_info":
                result = await ai.get_page_info()
                ai._step_elapsed = time.time() - ai._step_started_at
                entry.update({
                    "status": "success",
                    "page_info": result,
                    "elapsed": round(ai._step_elapsed, 2),
                })

            if entry.get("status") in ("success", "passed"):
                success_count += 1
                ctx.completed_steps.append(step_name)
            else:
                ctx.failed_step = step_name

        except Exception as e:
            logger.error(f"[YamlRunner] {step_name} error: {e}")
            ai._step_elapsed = time.time() - ai._step_started_at
            entry.update({
                "status": "failed",
                "error": str(e),
                "elapsed": round(ai._step_elapsed, 2),
            })
            ctx.failed_step = step_name

        results.append(entry)

        await event_bus.publish(Event(
            type="step_completed" if entry["status"] in ("success", "passed") else "step_failed",
            execution_id=eid,
            data={"step_id": step_name, "step_type": step_type},
        ))

        # Abort on failure (same default as BaseCase)
        if entry["status"] == "failed":
            logger.error(f"[YamlRunner] Step {step_name} failed, aborting")
            aborted = True
            break

    # --- Teardown ---
    await browser.close()
    await pw.stop()
    ctx.browser.mode = ""
    logger.info("[YamlRunner] Browser closed")

    total = len(steps)
    failed = total - success_count
    status = "completed" if failed == 0 else "failed"

    report: dict[str, Any] = {
        "case_name": case_name,
        "status": status,
        "source": "yaml",
        "total_steps": total,
        "success_count": success_count,
        "failed_count": failed,
        "steps": results,
        "elapsed_seconds": ctx.elapsed_seconds,
    }
    if aborted:
        report["aborted"] = True

    # Save report
    _save_yaml_report(report, rd)

    await event_bus.publish(Event(
        type="execution_completed",
        execution_id=eid,
        data={"report": report},
    ))

    return report


def list_yaml_cases(cases_root: Path) -> list[dict]:
    """List all YAML-defined cases in a directory tree.

    Looks for directories containing ``case.yaml`` or ``case.yml``.
    """
    cases = []
    if not cases_root.exists():
        return cases

    for yaml_file in sorted(cases_root.rglob("case.yaml")):
        d = yaml_file.parent
        case_id = d.name
        try:
            data = load_yaml_case(d)
            cases.append({
                "id": case_id,
                "name": data.get("name", case_id),
                "dir": str(d),
                "steps": data.get("steps", []),
                "source": "yaml",
            })
        except Exception as e:
            logger.warning(f"[YamlRunner] Failed to load case {case_id}: {e}")

    # Also check for case.yml
    for yaml_file in sorted(cases_root.rglob("case.yml")):
        d = yaml_file.parent
        case_id = d.name
        if any(c["id"] == case_id for c in cases):
            continue  # already found via case.yaml
        try:
            data = load_yaml_case(d)
            cases.append({
                "id": case_id,
                "name": data.get("name", case_id),
                "dir": str(d),
                "steps": data.get("steps", []),
                "source": "yaml",
            })
        except Exception as e:
            logger.warning(f"[YamlRunner] Failed to load case {case_id}: {e}")

    return cases


def _save_yaml_report(report: dict, case_dir: Path) -> None:
    """Save report.json to the case directory."""
    import json
    from datetime import datetime

    results_dir = case_dir / "test_results"
    ts_dir = results_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_dir.mkdir(parents=True, exist_ok=True)

    (ts_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"[YamlRunner] Report saved to {ts_dir}")
