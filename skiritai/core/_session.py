"""Shared browser session and report utilities for flow.py and yaml_runner.py."""
from __future__ import annotations

import base64
import json
import shutil
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
        Path(__file__).parent / "templates" / "report_vue.html",
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

        from skiritai.core.tools import set_browser
        set_browser(self._browser, self._context)

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


def _transform_for_vue(report: dict) -> dict:
    """Transform report data to match the Vue template's expected schema.

    The Vue StepCard expects each step to have ``verifications`` (array)
    and ``mode``.  Verify steps store assertion/reason as top-level keys
    which the Vue template can't render directly — this function moves
    them into the ``verifications`` array and builds a readable summary.
    """
    import copy
    data = copy.deepcopy(report)

    for step in data.get("steps", []):
        stype = step.get("type", "action")

        # Ensure every step has a verifications array
        if "verifications" not in step:
            step["verifications"] = []

        # Ensure every step has a mode field
        if "mode" not in step:
            step["mode"] = None

        # For verify steps: move assertion/reason into verifications array
        if stype == "verify":
            assertion = step.get("assertion", "")
            reason = step.get("reason", "")
            passed = step.get("status") in ("success", "passed")
            if assertion:
                step["verifications"].append({
                    "assertion": assertion,
                    "passed": passed,
                    "reason": reason,
                    "screenshot": None,
                })
            if not step.get("summary"):
                step["summary"] = assertion

    return data


def _copy_screenshots(report: dict, screenshots_dir: Path) -> None:
    """Copy screenshot files from tempdir into the report's screenshots/ directory."""
    for step in report.get("steps", []):
        for s in step.get("screenshots", []):
            spath = s.get("path", "")
            if not spath or spath.startswith("data:"):
                continue
            src = Path(spath)
            if not src.exists():
                continue
            dest = screenshots_dir / src.name
            if not dest.exists():
                shutil.copy2(src, dest)


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

    # Copy screenshots from tempdir to report dir
    screenshots_dir = ts_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    _copy_screenshots(report, screenshots_dir)

    # Update JSON paths to point to copied screenshots (relative to report dir)
    for step in report.get("steps", []):
        for s in step.get("screenshots", []):
            spath = s.get("path", "")
            if spath and not spath.startswith("data:"):
                src = Path(spath)
                if src.exists() and (screenshots_dir / src.name).exists():
                    s["path"] = str(screenshots_dir / src.name)

    # JSON report (machine-readable)
    (ts_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # HTML report (human-readable), using the shared template cache
    template = _load_template()
    prev_data = _load_previous_report(base_dir, ts_dir)
    if template:
        vue_data = _transform_for_vue(report)
        if prev_data:
            prev, prev_dir = prev_data
            comp = _build_comparison(prev, report, prev_dir.name)
            vue_data["comparison"] = comp
        # Embed screenshot data as base64 for self-contained HTML
        for step in vue_data.get("steps", []):
            for s in step.get("screenshots", []):
                spath = s.get("path", "")
                if spath and not spath.startswith("data:"):
                    try:
                        with open(spath, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                        s["path"] = f"data:image/png;base64,{b64}"
                    except Exception:
                        pass
        report_json = json.dumps(vue_data, ensure_ascii=False)
        html = template.replace('{"placeholder":true}', report_json)
        (ts_dir / "report.html").write_text(html, encoding="utf-8")

    prefix = f"[{label}]" if label else ""
    logger.info(f"{prefix} Report saved to {ts_dir}")

    # Write a comparison summary vs the previous run
    if prev_data:
        prev, prev_dir = prev_data
        _write_comparison_text(prev, report, prev_dir.name, ts_dir)

    return ts_dir


def _load_previous_report(base_dir: Path, current_dir: Path) -> tuple[dict, Path] | None:
    """Load the most recent previous run's report, or return None."""
    results_root = base_dir / "test_results"
    if not results_root.exists():
        return None

    prev_dirs = sorted(
        [d for d in results_root.iterdir() if d.is_dir() and d != current_dir],
        reverse=True,
    )
    if not prev_dirs:
        return None

    prev_report_file = prev_dirs[0] / "report.json"
    if not prev_report_file.exists():
        return None

    try:
        prev = json.loads(prev_report_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    return prev, prev_dirs[0]


def _build_comparison(prev: dict, current: dict, prev_dir_name: str) -> dict:
    """Build comparison data dict for the Vue report."""
    return {
        "prev_ok": prev.get("success_count", 0),
        "prev_total": prev.get("total_steps", 0),
        "prev_elapsed": prev.get("elapsed_seconds"),
        "prev_timestamp": prev_dir_name,
        "curr_ok": current.get("success_count", 0),
        "curr_total": current.get("total_steps", 0),
        "curr_elapsed": current.get("elapsed_seconds"),
    }


def _write_comparison_text(prev: dict, current: dict, prev_dir_name: str, current_dir: Path) -> None:
    """Write a brief comparison with the most recent previous run, if any."""
    c_total = current.get("total_steps", 0)
    c_ok = current.get("success_count", 0)
    c_elapsed = current.get("elapsed_seconds")

    p_total = prev.get("total_steps", 0)
    p_ok = prev.get("success_count", 0)
    p_elapsed = prev.get("elapsed_seconds")

    lines = [
        "Comparison with previous run:",
        f"  Prev: {p_ok}/{p_total} passed{f', {p_elapsed}s' if p_elapsed else ''} — {prev_dir_name}",
        f"  Curr: {c_ok}/{c_total} passed{f', {c_elapsed}s' if c_elapsed else ''}",
    ]
    if c_total == p_total and c_ok != p_ok:
        delta = c_ok - p_ok
        direction = "more" if delta > 0 else "fewer"
        lines.append(f"  Change: {abs(delta)} {direction} step(s) passed")

    comparison_text = "\n".join(lines) + "\n"
    (current_dir / "comparison.txt").write_text(comparison_text, encoding="utf-8")
    logger.info(comparison_text.strip())
