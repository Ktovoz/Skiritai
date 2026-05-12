"""Notification hooks — send execution results to external systems.

Configure via environment variables:

.. code-block:: bash

    # Slack-compatible webhook
    export SKIRITAI_WEBHOOK_URL="https://hooks.slack.com/services/..."

    # Optional: custom headers (JSON string)
    export SKIRITAI_WEBHOOK_HEADERS='{"Authorization": "Bearer xxx"}'

    # Only notify on failure (default: notify on all outcomes)
    export SKIRITAI_NOTIFY_ON_FAILURE_ONLY="true"

Supports any webhook that accepts JSON payloads (Slack, Discord, Teams, custom).
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from skiritai.logger import logger

# Maximum payload size for the notification snippet (chars).
_MAX_PAYLOAD = 3000


def _format_payload(report: dict) -> dict:
    """Build a webhook-friendly JSON payload from a test report."""
    status = report.get("status", "unknown")
    case_name = report.get("case_name", "unknown")
    total = report.get("total_steps", 0)
    success = report.get("success_count", 0)
    failed = report.get("failed_count", 0)
    elapsed = report.get("elapsed_seconds")

    emoji = "✅" if status == "completed" else "❌"
    title = f"{emoji} Skiritai: {case_name} — {status.upper()}"
    summary = f"{success}/{total} passed"
    if failed:
        summary += f", {failed} failed"

    # Failure details
    failures = []
    for step in report.get("steps", []):
        if step.get("status") in ("failed",):
            failures.append(
                f"- {step.get('step_id', '?')}: {step.get('error') or step.get('summary', 'no details')}"
            )

    text = f"{title}\n{summary}"
    if elapsed:
        text += f"\nElapsed: {elapsed}s"
    if failures:
        text += f"\n\nFailures:\n" + "\n".join(failures[:10])

    # Slack-compatible format
    return {
        "text": text[:2500],
        "attachments": [
            {
                "title": case_name,
                "text": text[:_MAX_PAYLOAD],
                "color": "good" if status == "completed" else "danger",
            }
        ],
    }


async def send_webhook(report: dict) -> bool:
    """Send a webhook notification for a completed test run.

    Reads ``SKIRITAI_WEBHOOK_URL`` from the environment.  No-op if not set.

    Args:
        report: The final report dict (after normalization).

    Returns:
        True if sent successfully, False on error or if not configured.
    """
    url = os.getenv("SKIRITAI_WEBHOOK_URL", "").strip()
    if not url:
        return False

    # Optional: only notify on failure
    notify_on_failure_only = os.getenv("SKIRITAI_NOTIFY_ON_FAILURE_ONLY", "").lower() in (
        "true", "1", "yes"
    )
    if notify_on_failure_only and report.get("status") == "completed":
        logger.debug("[Notify] Skipped: test passed and SKIRITAI_NOTIFY_ON_FAILURE_ONLY is set")
        return False

    payload = _format_payload(report)
    headers_raw = os.getenv("SKIRITAI_WEBHOOK_HEADERS", "{}")
    try:
        extra_headers = json.loads(headers_raw)
    except json.JSONDecodeError:
        extra_headers = {}

    headers = {"Content-Type": "application/json", **extra_headers}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _post():
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        status_code = await loop.run_in_executor(None, _post)
        # Log only the host — full URL may contain secret tokens in path
        host = url.split("/")[2] if "//" in url else url[:30]
        logger.info(f"[Notify] Webhook sent to {host} → HTTP {status_code}")
        return True
    except Exception as e:
        # Notifications are non-critical — don't fail the test
        logger.warning(f"[Notify] Webhook failed: {e}")
        return False


async def notify_if_configured(report: dict) -> None:
    """Send notifications for all configured channels.

    Add new channel backends here as they are implemented.

    Args:
        report: The normalized report dict.
    """
    await send_webhook(report)
