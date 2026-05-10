"""Shared test configuration for Skiritai tests."""
from unittest.mock import MagicMock

import pytest


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
    monkeypatch.setenv("SKIRITAI_HEADLESS", "true")
