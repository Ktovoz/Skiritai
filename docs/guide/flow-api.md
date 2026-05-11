# Flow API

The Flow API is a functional, no-subclass way to write tests. Instead of inheriting from `BaseCase`, you use an `async with` context manager.

## Basic Usage

```python
import asyncio
from skiritai import flow

async def main():
    async with flow() as ai:
        await ai.action("Navigate to https://www.baidu.com")
        await ai.screenshot("homepage")
        result = await ai.verify("Page title contains '百度'")
        print(f"Verify: {'PASS' if result['passed'] else 'FAIL'}")

asyncio.run(main())
```

`flow()` launches a browser, gives you an `ai` object, and automatically closes the browser when the block exits.

## Available Methods

| Method | Description |
|---|---|
| `ai.action(description, mode=None)` | Execute a natural-language action via the AI agent |
| `ai.verify(assertion, take_screenshot=True)` | Run an AI-powered assertion (non-blocking on failure) |
| `ai.screenshot(name)` | Capture a full-page screenshot |
| `ai.analyze_page()` | Analyze page DOM (cached, injected into subsequent `action()` calls) |
| `ai.get_page_info()` | Get page title, URL, and text summary (cached) |

## Configuration

```python
from pathlib import Path

async with flow(
    headless=True,                   # Run browser in headless mode
    results_dir=Path("results"),     # Directory for reports and screenshots
    max_steps=20,                    # Max agent tool-call steps per action
) as ai:
    await ai.action("...")
```

All parameters are optional. `headless` defaults to the `HEADLESS` environment variable.

## How It Differs from BaseCase

| Feature | BaseCase | Flow API |
|---|---|---|
| Structure | Class + decorators (`@step`, `@step_mode`) | Flat `async with` block |
| Browser lifecycle | Manual via `setup/teardown` | Automatic |
| Step tracking | Auto-generated from method names | Auto-generated step IDs |
| Best for | Structured test suites, reusable cases | Quick scripts, one-off exploration |
| Replay scripts | Per-step `.py` files in `scripts/` | Same Explore→Replay loop |
