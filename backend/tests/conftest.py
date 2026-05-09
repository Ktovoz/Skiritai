"""Shared test configuration for Skiritai backend tests."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Bootstrap: ensure backend package is importable
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


@pytest.fixture
def mock_page():
    """Create a mock Playwright page for unit tests."""
    page = MagicMock()
    page.url = "http://localhost"
    page.context = MagicMock()
    return page


@pytest.fixture
def headless_env(monkeypatch):
    """Set HEADLESS=true for tests that need it."""
    monkeypatch.setenv("HEADLESS", "true")
