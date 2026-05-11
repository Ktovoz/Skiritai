"""Shared browser session and report utilities for flow.py and yaml_runner.py."""
from __future__ import annotations

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
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()


def save_report(report: dict, base_dir: Path, label: str = "") -> Path:
    """Save report.json to ``<base_dir>/test_results/<timestamp>/report.json``.

    Args:
        report: The report dictionary.
        base_dir: Base directory (results_dir or case_dir).
        label: Optional label for log messages (e.g. "Flow", "YamlRunner").

    Returns:
        The directory where the report was saved.
    """
    ts_dir = base_dir / "test_results" / datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_dir.mkdir(parents=True, exist_ok=True)

    (ts_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    prefix = f"[{label}]" if label else ""
    logger.info(f"{prefix} Report saved to {ts_dir}")
    return ts_dir
