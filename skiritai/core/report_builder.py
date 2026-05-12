"""Shared report builder — normalizes step/report output across all APIs.

Ensures BaseCase, YAML runner, and Flow API produce the same report schema
so consumers (Web API, Vue report, CLI) see a consistent structure.
"""
from __future__ import annotations

from typing import Any


def normalize_step(step: dict, *, default_type: str = "action") -> dict:
    """Normalize a single step entry to the canonical schema.

    Canonical step schema:
        {
            "step_id": str,
            "type": str,          # "action" | "verify" | "screenshot" | "analyze" | "page_info"
            "status": str,        # "success" | "failed" (verify: "passed" → "success")
            "mode": str | null,   # "replay" | "explore" | null (for non-action types)
            "summary": str | null,
            "assertion": str | null,  # only for verify steps
            "reason": str | null,     # only for verify steps
            "error": str | null,
            "elapsed": float | null,
            "screenshots": list[dict],
        }
    """
    normalized: dict[str, Any] = {}

    # ---- Required fields ----
    normalized["step_id"] = step.get("step_id", "unknown")

    # Type: explicit > default
    normalized["type"] = step.get("type", default_type)

    # Status: normalize "passed" → "success" for consistency
    raw_status = step.get("status", "failed")
    if raw_status == "passed":
        normalized["status"] = "success"
    elif raw_status in ("success", "failed", "skipped"):
        normalized["status"] = raw_status
    else:
        normalized["status"] = "failed"

    # Mode (only meaningful for action-type steps)
    normalized["mode"] = step.get("mode") if step.get("mode") else None

    # ---- Optional fields ----
    normalized["summary"] = step.get("summary")
    normalized["assertion"] = step.get("assertion")
    normalized["reason"] = step.get("reason")
    normalized["error"] = step.get("error")
    normalized["elapsed"] = step.get("elapsed")
    normalized["screenshots"] = step.get("screenshots", [])

    # Remove None-valued keys for cleaner JSON
    return {k: v for k, v in normalized.items() if v is not None}


def normalize_report(report: dict, *, source: str = "python") -> dict:
    """Normalize a full report dict to the canonical schema.

    Canonical report schema:
        {
            "case_name": str,
            "source": str,            # "python" | "yaml" | "flow"
            "status": str,            # "completed" | "failed"
            "total_steps": int,
            "success_count": int,
            "failed_count": int,
            "steps": [canonical step...],
            "elapsed_seconds": float | null,
            "error": str | null,
            "aborted": bool,
        }
    """
    steps = report.get("steps", [])
    # Determine default type: if source="yaml" steps already have type;
    # Python/BaseCase steps are always "action".
    default_type = "action"

    normalized_steps = []
    for step in steps:
        default_type = step.get("type", "action")
        normalized_steps.append(normalize_step(step, default_type=default_type))

    report_source = report.get("source", source)

    result: dict[str, Any] = {
        "case_name": report.get("case_name", "unknown"),
        "source": report_source,
        "status": report.get("status", "failed"),
        "total_steps": report.get("total_steps", len(steps)),
        "success_count": report.get("success_count", 0),
        "failed_count": report.get("failed_count", 0),
        "steps": normalized_steps,
        "elapsed_seconds": report.get("elapsed_seconds"),
        "error": report.get("error"),
    }
    # Only include optional fields when present/truthy
    if report.get("aborted"):
        result["aborted"] = True
    return result
