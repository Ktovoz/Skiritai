"""Shared browser session and report utilities for flow.py and yaml_runner.py."""
from __future__ import annotations

import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from skiritai.core.browser import get_launch_args
from skiritai.core.case_context import CaseContext
from skiritai.logger import logger

# Type alias for the optional log callback used across the framework.
OnLogCallback = Callable[[str], Any] | None

# Cached HTML report template (loaded once per process)
_template_html: str | None = None


def _load_template() -> str | None:
    """Load the Vue + Ant Design report template, cached across all runners."""
    global _template_html
    if _template_html is not None:
        return _template_html

    template_paths = [
        Path(__file__).parent.parent.parent / "report" / "dist" / "index.html",
        Path(__file__).parent / "templates" / "report.html",
    ]
    for tp in template_paths:
        if tp.exists():
            _template_html = tp.read_text(encoding="utf-8")
            return _template_html
    return None


class BrowserSession:
    """Manages a Playwright browser lifecycle.

    Used by both :class:`FlowAI` and :func:`run_yaml_case` to avoid
    duplicating browser launch/close boilerplate.
    """

    def __init__(self, headless: bool | None = None):
        self._headless = headless
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._started_at: float = 0.0

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started. Use async with or call start().")
        return self._page

    @property
    def started_at(self) -> float:
        return self._started_at

    async def start(self) -> None:
        """Launch browser and create a new page."""
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(**get_launch_args(self._headless))
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        self._started_at = time.time()

    async def stop(self) -> None:
        """Close browser and stop Playwright."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        self._page = None

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()


def save_report(report: dict, base_dir: Path, label: str = "") -> Path:
    """Save report.json and report.html to ``<base_dir>/test_results/<timestamp>/``.

    Args:
        report: The report dictionary.
        base_dir: Base directory (results_dir or case_dir).
        label: Optional label for log messages (e.g. "Flow", "YamlRunner").

    Returns:
        The directory where the report was saved.
    """
    ts_dir = base_dir / "test_results" / datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_dir.mkdir(parents=True, exist_ok=True)

    # JSON report (machine-readable)
    (ts_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # HTML report (human-readable), using the shared template cache
    template = _load_template()
    if template:
        # Embed screenshot data as base64 for offline report
        for step in report.get("steps", []):
            for s in step.get("screenshots", []):
                spath = s.get("path", "")
                if spath and not spath.startswith("data:"):
                    try:
                        with open(spath, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                        s["path"] = f"data:image/png;base64,{b64}"
                    except Exception:
                        pass
        report_json = json.dumps(report, ensure_ascii=False)
        html = template.replace('{"placeholder":true}', report_json)
        (ts_dir / "report.html").write_text(html, encoding="utf-8")

    prefix = f"[{label}]" if label else ""
    logger.info(f"{prefix} Report saved to {ts_dir}")

    # Write a comparison summary vs the previous run
    _write_comparison(base_dir, report, ts_dir)

    return ts_dir


def _write_comparison(base_dir: Path, current: dict, current_dir: Path) -> None:
    """Write a brief comparison with the most recent previous run, if any."""
    results_root = base_dir / "test_results"
    if not results_root.exists():
        return

    # Find previous run dirs (sorted by name = timestamp)
    prev_dirs = sorted(
        [d for d in results_root.iterdir() if d.is_dir() and d != current_dir],
        reverse=True,
    )
    if not prev_dirs:
        return

    prev_report_file = prev_dirs[0] / "report.json"
    if not prev_report_file.exists():
        return

    try:
        prev = json.loads(prev_report_file.read_text(encoding="utf-8"))
    except Exception:
        return

    c_total = current.get("total_steps", 0)
    c_ok = current.get("success_count", 0)
    c_fail = current.get("failed_count", 0)
    c_elapsed = current.get("elapsed_seconds")

    p_total = prev.get("total_steps", 0)
    p_ok = prev.get("success_count", 0)
    p_fail = prev.get("failed_count", 0)
    p_elapsed = prev.get("elapsed_seconds")

    lines = [
        "Comparison with previous run:",
        f"  Prev: {p_ok}/{p_total} passed{f', {p_elapsed}s' if p_elapsed else ''} — {prev_dirs[0].name}",
        f"  Curr: {c_ok}/{c_total} passed{f', {c_elapsed}s' if c_elapsed else ''}",
    ]
    if c_total == p_total and c_ok != p_ok:
        delta = c_ok - p_ok
        direction = "more" if delta > 0 else "fewer"
        lines.append(f"  Change: {abs(delta)} {direction} step(s) passed")

    comparison_text = "\n".join(lines) + "\n"
    (current_dir / "comparison.txt").write_text(comparison_text, encoding="utf-8")
    logger.info(comparison_text.strip())
