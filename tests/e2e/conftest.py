"""Shared fixtures for E2E tests — local HTTP server and case directories."""
from __future__ import annotations

import http.server
import os
import shutil
import tempfile
import threading
from pathlib import Path

import pytest

# Force headless mode for E2E tests
os.environ["SKIRITAI_HEADLESS"] = "true"

# ============================================================
# Test HTML Page
# ============================================================

TEST_PAGE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>E2E Test Page</title></head>
<body>
    <h1 id="title">Test Page</h1>
    <input id="text-input" type="text" placeholder="Enter text">
    <button id="submit-btn">Submit</button>
    <div id="result"></div>
    <select id="color-select">
        <option value="red">Red</option>
        <option value="blue">Blue</option>
        <option value="green">Green</option>
    </select>
    <script>
        document.getElementById('submit-btn').addEventListener('click', function() {
            var inputVal = document.getElementById('text-input').value;
            document.getElementById('result').textContent = 'Result: ' + inputVal;
        });
    </script>
</body>
</html>
"""


# ============================================================
# Local HTTP Server
# ============================================================

class _TestHandler(http.server.BaseHTTPRequestHandler):
    """Serves TEST_PAGE_HTML for all GET requests."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(TEST_PAGE_HTML.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # suppress console noise during tests


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def case_url():
    """Start a local HTTP server and return (url, port)."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _TestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}", port
    server.shutdown()
    server.server_close()


@pytest.fixture
def simple_case(case_url):
    """Create a temporary case directory with case.py and replay scripts."""
    url, _ = case_url
    tmpdir = tempfile.mkdtemp(prefix="e2e_case_")
    case_dir = Path(tmpdir) / "e2e_test_case"
    case_dir.mkdir()

    case_py = (
        "from skiritai.core.base_case import BaseCase\n"
        "\n"
        "class E2ETestCase(BaseCase):\n"
        "\n"
        "    async def setup(self):\n"
        "        await self.launch_browser()\n"
        "\n"
        "    async def teardown(self):\n"
        "        await self.close_browser()\n"
        "\n"
        "    async def fill_and_submit(self, ai):\n"
        '        """Fill input and click submit."""\n'
        '        await ai.action("fill input and click submit")\n'
    )
    (case_dir / "case.py").write_text(case_py, encoding="utf-8")

    scripts_dir = case_dir / "scripts"
    scripts_dir.mkdir()
    replay_script = (
        "# Auto-generated replay script\n"
        "# Step: fill_and_submit\n"
        "\n"
        "async def run(page, context):\n"
        f'    await page.goto("{url}")\n'
        '    await page.wait_for_load_state("networkidle")\n'
        '    await page.fill("#text-input", "Hello E2E")\n'
        '    await page.click("#submit-btn")\n'
    )
    (scripts_dir / "fill_and_submit.py").write_text(replay_script, encoding="utf-8")

    yield case_dir, url
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def multi_step_case(case_url):
    """Create a case with two steps for API lifecycle testing."""
    url, _ = case_url
    tmpdir = tempfile.mkdtemp(prefix="e2e_multi_")
    parent = Path(tmpdir)
    case_dir = parent / "e2e_multi_case"
    case_dir.mkdir()

    case_py = (
        "from skiritai.core.base_case import BaseCase\n"
        "\n"
        "class E2EMultiStepCase(BaseCase):\n"
        "\n"
        "    async def setup(self):\n"
        "        await self.launch_browser()\n"
        "\n"
        "    async def teardown(self):\n"
        "        await self.close_browser()\n"
        "\n"
        "    async def navigate_page(self, ai):\n"
        '        """Navigate to test page."""\n'
        '        await ai.action("navigate to test page")\n'
        "\n"
        "    async def fill_form(self, ai):\n"
        '        """Fill and submit the form."""\n'
        '        await ai.action("fill form and submit")\n'
    )
    (case_dir / "case.py").write_text(case_py, encoding="utf-8")

    scripts_dir = case_dir / "scripts"
    scripts_dir.mkdir()

    (scripts_dir / "navigate_page.py").write_text(
        "# Auto-generated replay script\n"
        "# Step: navigate_page\n"
        "\n"
        "async def run(page, context):\n"
        f'    await page.goto("{url}")\n'
        '    await page.wait_for_load_state("networkidle")\n',
        encoding="utf-8",
    )

    (scripts_dir / "fill_form.py").write_text(
        "# Auto-generated replay script\n"
        "# Step: fill_form\n"
        "\n"
        "async def run(page, context):\n"
        f'    await page.goto("{url}")\n'
        '    await page.wait_for_load_state("networkidle")\n'
        '    await page.fill("#text-input", "Multi Step")\n'
        '    await page.click("#submit-btn")\n',
        encoding="utf-8",
    )

    yield case_dir, "e2e_multi_case", url
    shutil.rmtree(tmpdir, ignore_errors=True)
