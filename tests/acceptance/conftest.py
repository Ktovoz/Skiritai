"""Acceptance tests — shared helpers for case construction."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

# Cleanup generated scripts before test session
_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
if _SCRIPTS_DIR.exists():
    import shutil

    shutil.rmtree(_SCRIPTS_DIR)


def _make_mock_page(url: str = "http://localhost") -> MagicMock:
    page = MagicMock()
    page.url = url
    page.context = MagicMock()
    return page


def _make_case(tmpdir: str, steps: list[tuple[str, str | None]] | None = None):
    """Create a temporary case directory with a case.py.

    Args:
        tmpdir: temp directory path
        steps: list of (method_name, step_mode_or_None)
    """
    from pathlib import Path
    from skiritai.core.base_case import BaseCase, step_mode

    case_dir = Path(tmpdir) / "test_case"
    case_dir.mkdir(parents=True, exist_ok=True)

    methods = {
        "setup": lambda self: _noop_setup(self),
        "teardown": lambda self: _noop_teardown(self),
    }

    if steps:
        for name, mode in steps:
            if mode:
                decorated = step_mode(mode)(_make_step_fn(name))
            else:
                decorated = _make_step_fn(name)
            methods[name] = decorated

    TestCase = type("TestCase", (BaseCase,), methods)
    return case_dir, TestCase


async def _noop_setup(self):
    self._page = _make_mock_page()


async def _noop_teardown(self):
    pass


def _make_step_fn(name):
    async def step(self, ai):
        return await ai.action(f"do {name}")

    step.__name__ = name
    return step
