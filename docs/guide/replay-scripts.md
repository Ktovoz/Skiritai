# Replay Scripts

After exploration, the AI agent generates standalone Python scripts that replay the exact same actions — at ~30x speed,
with zero LLM overhead.

## How It Works

1. **Explore phase** — AI agent analyzes the page, invokes tools (click, fill, navigate, etc.), and records every action
2. **Script generation** — Tool-call history is compiled into a standalone `.py` file using direct Playwright API calls
3. **Replay phase** — The generated script runs against Playwright without any AI involvement

## Script Structure

Generated scripts follow a standard pattern:

```python
"""Auto-generated replay script — can be run independently."""
import asyncio
import os
from playwright.async_api import async_playwright


async def run(page, context):
    await page.goto("https://example.com")
    await page.wait_for_load_state("networkidle")
    await page.click("#login-button")
    await page.fill("#username", "admin")
    await page.fill("#password", "secret")
    await page.click("#submit")


if __name__ == "__main__":
    async def main():
        pw = await async_playwright().start()
        headless = (os.getenv("SKIRITAI_HEADLESS") or os.getenv("HEADLESS", "false")).lower() in ("true", "1", "yes")
        browser = await pw.chromium.launch(headless=headless)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        try:
            await run(page, ctx)
        finally:
            await browser.close()
            await pw.stop()

    asyncio.run(main())
```

Scripts are saved to `<case_dir>/scripts/<step_name>.py`.

## Running Scripts

### Standalone

```bash
python scripts/my_step.py
```

### Import and Run

```python
import importlib.util
spec = importlib.util.spec_from_file_location("script", "scripts/my_step.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
await module.run(page, context)
```

## Read-Only Tool Filtering

Replay scripts only include **action** tools (navigate, click, fill, etc.). **Perception** and read-only tools are
excluded:

| Excluded tool   | Reason                                             |
|-----------------|----------------------------------------------------|
| `page_perceive` | Read-only DOM analysis, not needed at replay speed |
| `find_element`  | Read-only search, selectors already determined     |
| `get_page_info` | Read-only metadata                                 |
| `get_text`      | Read-only content extraction                       |
| `response`      | Final summary, not an action                       |

## Script Management API

### List Scripts

```bash
GET /api/cases/{id}/scripts
```

Returns all generated replay scripts for a case with their content.

### Get Script Content

```bash
GET /api/cases/{id}/scripts/{step}
```

Returns the full script content for a specific step.

### Edit Script

```bash
PUT /api/cases/{id}/scripts/{step}
Content-Type: application/json

{"content": "async def run(page, context):\n    await page.goto('...')"}
```

Useful for fine-tuning generated scripts without re-exploring.

### Solidify Script

```bash
POST /api/cases/{id}/scripts/{step}/solidify
```

Creates a `.solidified` marker file. A solidified script is considered final and ready for replay mode.

## Script Lifecycle

```
Explore → Generate → Solidify → Replay
  │                      │
  │   auto-saved to      │   marks script as
  │   scripts/<step>.py  │   ready for production use
  │                      │
  └──────────────────────┘
```

## Local Script Files

```
case_dir/
├── case.py
├── scripts/
│   ├── my_step.py           # Auto-generated replay script
│   ├── .my_step.solidified   # Solidification marker
│   ├── another_step.py
│   └── .another_step.solidified
└── ...
```
