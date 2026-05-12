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

Step-level options (per step dict):
    - ``on_failure``: ``abort`` (default) | ``skip`` | ``retry`` — controls what happens when the step fails
    - ``max_retries``: Number of retries when ``on_failure: retry`` (default: 1)

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

from skiritai.core._session import BrowserSession, OnLogCallback, save_report
from skiritai.core.ai_context import AIContext
from skiritai.core.case_context import CaseContext
from skiritai.events import Event, event_bus
from skiritai.logger import logger
from skiritai.core.notify import notify_if_configured

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def _require_yaml() -> None:
    if yaml is None:
        raise ImportError(
            "PyYAML is required for YAML cases. Install with: pip install PyYAML"
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


# ---- Failure policy for YAML steps ----

def _step_failure_policy(step_def: dict) -> tuple[str, int]:
    """Return the failure policy and max retries for a YAML step.

    Returns:
        (policy, max_retries) tuple.  policy is one of "abort", "skip", "retry".
    """
    raw = step_def.get("on_failure", "abort")
    if isinstance(raw, str) and raw.lower() in ("abort", "skip", "retry"):
        policy = raw.lower()
    else:
        policy = "abort"
    max_retries = int(step_def.get("max_retries", 1)) if policy == "retry" else 0
    return policy, max_retries


# ---- Step execution helpers ----

async def _exec_action(ai: AIContext, arg: str) -> tuple[str, dict]:
    result = await ai.action(str(arg))
    ok = result.get("success", False)
    status = "success" if ok else "failed"
    entry = {
        "status": status,
        "mode": "replay" if ai.has_replay() else "explore",
        "summary": result.get("summary", ""),
    }
    return status, entry


async def _exec_verify(ai: AIContext, arg: str) -> tuple[str, dict]:
    result = await ai.verify(str(arg))
    passed = result.get("passed", False)
    status = "passed" if passed else "failed"
    entry = {
        "status": status,
        "assertion": str(arg),
        "reason": result.get("reason", ""),
    }
    return status, entry


async def _exec_screenshot(ai: AIContext, arg: str) -> tuple[str, dict]:
    path = await ai.screenshot(str(arg))
    return "success", {"status": "success", "screenshot": path}


async def _exec_analyze(ai: AIContext, _arg: str) -> tuple[str, dict]:
    await ai.analyze_page()
    return "success", {"status": "success"}


async def _exec_page_info(ai: AIContext, _arg: str) -> tuple[str, dict]:
    info = await ai.get_page_info()
    return "success", {"status": "success", "page_info": info}


_STEP_EXECUTORS = {
    "action": _exec_action,
    "verify": _exec_verify,
    "screenshot": _exec_screenshot,
    "analyze": _exec_analyze,
    "page_info": _exec_page_info,
}


async def run_yaml_case(
    case_dir: Path,
    on_log: OnLogCallback = None,
    execution_id: str | None = None,
    results_dir: Path | None = None,
    llm=None,
    step_filter: list[str] | None = None,
) -> dict:
    """Run a YAML-defined test case.

    Args:
        case_dir: Directory containing ``case.yaml``.
        on_log: Optional callback for real-time log streaming.
        execution_id: Execution identifier for events.
        results_dir: Directory for saving results.
        llm: Optional LLM provider instance. If None, auto-detects from env.
        step_filter: Optional list of step names to run. None = run all.

    Returns:
        Report dict with case_name, status, steps, etc.
    """
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

    # --- Browser lifecycle (shared BrowserSession) ---
    session = BrowserSession(headless=headless)
    await session.start()
    ctx = CaseContext(case_dir=case_dir, execution_id=eid)
    ctx.browser.started_at = time.time()

    logger.info(f"[YamlRunner] {case_name} — {len(steps)} steps")

    await event_bus.publish(Event(
        type="execution_started",
        execution_id=eid,
        data={"case_name": case_name, "source": "yaml"},
    ))

    # Navigate to start URL if specified
    if start_url:
        await session.page.goto(start_url)
        await session.page.wait_for_load_state("networkidle")
        logger.info(f"[YamlRunner] Navigated to {start_url}")

    # --- Execute steps ---
    # Reuse a single AIContext across steps so analyze_page data persists.
    ai: AIContext | None = None
    results: list[dict] = []
    success_count = 0
    aborted = False

    for i, step_def in enumerate(steps):
        step_name = step_def.get("name", f"step_{i + 1}")

        # Filter steps if requested
        if step_filter and step_name not in step_filter:
            logger.info(f"[YamlRunner] Skipping {step_name} (not in filter)")
            continue

        # Determine step type and argument
        step_type = None
        step_arg = None
        for key in ("action", "verify", "screenshot", "analyze", "page_info"):
            if key in step_def:
                step_type = key
                step_arg = step_def[key]
                break

        if step_type is None:
            logger.warning(
                f"[YamlRunner] Unknown step type at index {i} (step '{step_name}'): "
                f"{list(step_def.keys())}. Skipping. "
                f"Valid step types: action, verify, screenshot, analyze, page_info"
            )
            results.append({
                "step_id": step_name,
                "type": "unknown",
                "status": "skipped",
                "error": f"Unknown step keys: {list(step_def.keys())}",
            })
            continue

        await event_bus.publish(Event(
            type="step_started",
            execution_id=eid,
            data={"step_id": step_name, "step_type": step_type},
        ))
        logger.info(f"[YamlRunner] {step_name} ({step_type}): {step_arg}")

        # Advance AIContext for new step, carrying over perception cache
        if ai is not None:
            ai = ai.copy_for_step(step_name)
        else:
            ai = AIContext(
                page=session.page,
                case_dir=case_dir,
                step_id=step_name,
                on_log=on_log,
                default_mode="auto",
                execution_id=eid,
                max_steps=max_steps,
                llm=llm,
            )
        ai._step_started_at = time.time()

        policy, max_retries = _step_failure_policy(step_def)
        attempt_limit = max_retries + 1  # 1 initial + N retries

        entry: dict[str, Any] = {
            "step_id": step_name,
            "type": step_type,
        }
        status = "failed"

        for attempt in range(attempt_limit):
            if attempt > 0:
                logger.info(f"[YamlRunner] Retrying {step_name} (attempt {attempt + 1}/{attempt_limit})")
            ai._step_started_at = time.time()  # reset per attempt

            try:
                executor = _STEP_EXECUTORS.get(step_type)
                if executor is None:
                    raise ValueError(f"Unknown step type: {step_type}")

                status, detail = await executor(ai, str(step_arg))
                ai._step_elapsed = time.time() - ai._step_started_at
                detail["elapsed"] = round(ai._step_elapsed, 2)
                entry.update(detail)

                if status in ("success", "passed"):
                    break  # succeeded, exit retry loop

            except Exception as e:
                logger.error(f"[YamlRunner] {step_name} error (attempt {attempt + 1}): {e}")
                ai._step_elapsed = time.time() - ai._step_started_at
                entry.update({
                    "status": "failed",
                    "error": str(e),
                    "elapsed": round(ai._step_elapsed, 2),
                })
                status = "failed"
                if attempt < attempt_limit - 1:
                    continue  # retry

        if status in ("success", "passed"):
            success_count += 1
            ctx.completed_steps.append(step_name)
        else:
            ctx.failed_step = step_name

        results.append(entry)

        await event_bus.publish(Event(
            type="step_completed" if entry.get("status") in ("success", "passed") else "step_failed",
            execution_id=eid,
            data={"step_id": step_name, "step_type": step_type},
        ))

        # Handle failure based on on_failure policy
        if entry.get("status") in ("failed",) and status not in ("success", "passed"):
            if policy == "skip":
                logger.warning(f"[YamlRunner] Step {step_name} failed, skipping (on_failure=skip)")
            elif policy == "retry":
                logger.error(f"[YamlRunner] Step {step_name} failed after {attempt_limit} attempt(s), aborting")
                aborted = True
                break
            else:
                logger.error(f"[YamlRunner] Step {step_name} failed, aborting (on_failure=abort)")
                aborted = True
                break

    # --- Teardown ---
    await session.stop()
    logger.info("[YamlRunner] Browser closed")

    total = len(results)
    failed = total - success_count
    status = "completed" if failed == 0 else "failed"

    # Warn if step_filter excluded all steps
    if step_filter and total == 0:
        logger.warning(
            f"[YamlRunner] No steps matched filter {step_filter}. "
            f"Available steps: {[s.get('name', f'step_{i+1}') for i, s in enumerate(steps)]}"
        )

    from skiritai.core.report_builder import normalize_report

    raw_report: dict[str, Any] = {
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
        raw_report["aborted"] = True

    report = normalize_report(raw_report)
    save_report(report, rd, label="YamlRunner")

    await event_bus.publish(Event(
        type="execution_completed",
        execution_id=eid,
        data={"report": report},
    ))

    # Fire-and-forget notification (non-blocking, best-effort)
    notify_if_configured(report)

    return report


def list_yaml_cases(cases_root: Path) -> list[dict]:
    """List all YAML-defined cases in a directory tree.

    Looks for directories containing ``case.yaml`` or ``case.yml``.
    Deduplicates by resolved directory path (not just directory name).
    """
    cases = []
    seen_paths: set[str] = set()
    if not cases_root.exists():
        return cases

    for pattern in ("case.yaml", "case.yml"):
        for yaml_file in sorted(cases_root.rglob(pattern)):
            d = yaml_file.parent.resolve()
            d_key = str(d)
            if d_key in seen_paths:
                continue
            seen_paths.add(d_key)
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

    return cases
