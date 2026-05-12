<div align="center">

# Skiritai

**AI-Powered Test Automation Agent**

<em>Named after the Skiritai — Sparta's elite reconnaissance troops who scouted the path ahead of the main army.</em>

<br>

[![Version](https://img.shields.io/badge/version-0.0.3-blue)](https://github.com/Ktovoz/Skiritai/releases)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Test Status](https://img.shields.io/github/actions/workflow/status/Ktovoz/Skiritai/test.yml?branch=main&label=test%20status)](https://github.com/Ktovoz/Skiritai/actions/workflows/test.yml)
[![Publish](https://img.shields.io/github/actions/workflow/status/Ktovoz/Skiritai/publish.yml?branch=main&label=publish)](https://github.com/Ktovoz/Skiritai/actions/workflows/publish.yml)

[English](README.md) | [中文](README_zh.md)

</div>

---

## What is Skiritai?

Skiritai is an AI-driven browser test automation framework that **scouts automation paths before executing them**.

Like the ancient Skiritai who reconnoitered the terrain before the Spartan army advanced, Skiritai's agent first *
*explores** the target application — navigating pages, discovering UI elements, and figuring out the correct sequence of
actions — then **generates replayable scripts** that can execute the same path at 30x speed without any AI inference.

```
Explore Mode (Scout the path)
  AI Agent → analyze page → decide actions → generate scripts
         ↓
Replay Mode (Execute the proven path)
  Script → direct execution → no AI needed → 30x faster
```

## Key Features

| Feature                   | Description                                                                               |
|---------------------------|-------------------------------------------------------------------------------------------|
| **Explore → Replay Loop** | AI explores and generates scripts on first run; replays them instantly on subsequent runs |
| **30x Performance**       | Replay mode skips AI inference entirely — 74s → 2.5s                                      |
| **Flow API**               | Functional, no-subclass API — `async with flow() as ai:`                                  |
| **YAML Cases**             | Define test steps in YAML, run via CLI or `run_yaml_case()`                              |
| **Python-native Cases**   | Define test cases as Python classes with decorators                                       |
| **Auto-Solidification**   | Successful explorations are automatically saved as replayable scripts                     |
| **Multi-level Fallback**  | `fill` → `click_force` → `eval_js` for resilient element interaction                      |
| **Flexible LLM**          | Supports OpenAI, Anthropic, Qwen, and any compatible API                                  |
| **Optional Web UI**       | FastAPI backend with REST + WebSocket for external frontends                              |
| **Visual Reports**        | Standalone HTML report built with Vue 3 + Ant Design — screenshots, assertions, step details |
| **CLI**                   | `skiritai run/serve/list/browser` commands                                                |

## How It Works

```python
from skiritai import BaseCase, step_mode


class SearchTest(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_site(self):
        await self.ai.action("Navigate to https://example.com")

    @step_mode("explore")  # Force AI exploration for this step
    async def search(self):
        await self.ai.action("Search for 'automation testing'")

    async def verify(self):
        await self.ai.action("Verify search results are displayed")
```

**First run** — AI explores each step, generates scripts:

```
[Step] open_site   (explore)  → 20s  → scripts/open_site.py   ✓
[Step] search      (explore)  → 30s  → scripts/search.py      ✓
[Step] verify      (explore)  → 24s  → scripts/verify.py      ✓
Total: 74s
```

**Second run** — scripts replay directly, no AI:

```
[Step] open_site   (replay)   → 0.8s → direct execution       ✓
[Step] search      (replay)   → 0.8s → direct execution       ✓
[Step] verify      (replay)   → 0.8s → direct execution       ✓
Total: 2.5s
```

### Flow API (Functional, No Subclass)

```python
from skiritai import flow

async with flow() as ai:
    await ai.action("Navigate to https://example.com")
    await ai.screenshot("homepage")
    await ai.verify("Page title contains 'Example'")
```

`flow()` is a functional context manager — no subclass, no decorators. Just `ai.action()`, `ai.verify()`, `ai.screenshot()`, `ai.analyze_page()`, and `ai.get_page_info()`.

### YAML Cases (No Code)

```yaml
# case.yaml
name: Search Test
steps:
  - action: Open https://www.baidu.com
  - action: Search for "Playwright"
  - verify: Search results are displayed
  - screenshot: result
```

```bash
skiritai run examples/baidu_yaml
```

YAML cases are perfect for QA teams who want AI-driven testing without writing Python. Supports `action`, `verify`, `screenshot`, `analyze`, `page_info` steps, with per-step `on_failure: skip | abort` policies.

## Quick Start

### 1. Install

```bash
pip install skiritai
playwright install chromium
```

### 2. Configure

```bash
# .env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. Run

```bash
# Run an example case
skiritai run examples/tutorial/minimal

# List available cases
skiritai list examples/
```

Or programmatically:

```python
import asyncio
from pathlib import Path
from skiritai import run_case

report = asyncio.run(run_case(Path("examples/minimal")))
print(report)
```

### 4. (Optional) Start Web Server

```bash
pip install skiritai[web]
skiritai serve --host 0.0.0.0 --port 8000
```

## Project Structure

```
skiritai/
├── core/                      # Core engine (always installed)
│   ├── agent_loop.py          # LangGraph ReAct Agent
│   ├── ai_context.py          # Explore/Replay execution context
│   ├── base_case.py           # Test case base class
│   ├── runner.py              # Case discovery and execution
│   ├── flow.py                # Functional no-subclass API
│   ├── yaml_runner.py         # YAML case loader and runner
│   ├── tools.py               # Playwright tool set (14 tools)
│   ├── browser.py             # Browser lifecycle management
│   └── ...
├── llm/                       # LLM provider abstraction
│   ├── openai_provider.py
│   └── anthropic_provider.py
├── events/                    # Event bus
├── web/                       # [optional] FastAPI server (pip install skiritai[web])
│   ├── app.py                 # Application factory
│   ├── routers/               # REST + WebSocket endpoints
│   └── ws_manager.py          # Event → WebSocket bridge
└── cli.py                     # CLI entry point

report/                        # Visual report project (Vue 3 + Ant Design)
├── src/                       #   Components: ReportHeader, SummaryBar, StepCard, ScreenshotViewer
├── dist/                      #   Build output (single-file HTML, data injected by _render_html)
└── package.json               #   skiritai-report

examples/                      # Sample test cases
├── tutorial/                  # Teaching examples (learn framework features)
│   ├── minimal/               #   Pure Playwright, no AI needed
│   ├── step_modes/            #   auto/explore/replay execution modes
│   ├── failure_policies/      #   ABORT/SKIP/RETRY failure strategies
│   ├── hooks_demo/            #   before_step/after_step/on_step_error hooks
│   └── context_demo/          #   Cross-step context sharing via self.ctx
├── baidu_search/              # [First Try] Full E2E AI-driven test + replay scripts
└── ktovoz_blog/               # [Advanced] 11-step long-range blog test

tests/                         # Framework tests
├── unit/
├── functional/
├── acceptance/
└── e2e/
```

## Examples

Examples are organized into three tiers:

### New Ways to Write Tests (no BaseCase needed)

| Example | Description |
|---|---|
| `flow_demo/` | Functional Flow API — `async with flow() as ai:` style, no subclass |
| `baidu_yaml/` | YAML-defined test case — write tests entirely in YAML |

### Teaching (learn framework features)

| Example | What It Teaches |
|---|---|
| `minimal/` | BaseCase structure — pure Playwright, no LLM required |
| `step_modes/` | `auto` / `explore` / `replay` execution modes via `@step_mode` |
| `failure_policies/` | `@on_failure(SKIP)` / `@on_failure(RETRY)` error handling |
| `hooks_demo/` | `before_step` / `after_step` / `on_step_error` lifecycle hooks |
| `context_demo/` | Cross-step data sharing with `self.ctx.store` |

### First Try (real-world end-to-end)

| Example | Description |
|---|---|
| `baidu_search/` | Complete E2E: open Baidu → search → verify results. Demonstrates Explore→Replay loop in a real scenario. |

### Advanced (long-range testing)

| Example | Description |
|---|---|
| `ktovoz_blog/` | 11-step blog test: homepage, articles, tags, about, footer, search, summary. Demonstrates the framework's capability for complex multi-step scenarios. |

```bash
# Flow API — functional style, no subclass
python examples/flow_demo/demo.py

# YAML case — no Python code at all
skiritai run examples/baidu_yaml

# Start with a teaching example (no AI needed)
skiritai run examples/tutorial/minimal

# Try a real-world test (needs LLM configured)
skiritai run examples/baidu_search

# Advanced long-range test
skiritai run examples/ktovoz_blog
```

## Roadmap

### Vision Perception Layer

Current AI exploration relies on DOM analysis and CSS selectors. The next evolution adds **visual perception** — the agent will "see" the page like a human tester, enabling:

- **Visual-based AI exploration** — interpret screenshots, identify UI elements by appearance, and interact with canvas/WebGL-based interfaces that lack accessible DOM
- **Multimodal model support** — leverage vision-language models (GPT-4o, Claude 3.5 Sonnet, Gemini) and native multimodal models for richer page understanding
- **Visual regression detection** — compare screenshots across runs to catch unexpected UI changes

### Multi-Platform Testing

Skiritai currently supports **Web** (Playwright/Chromium). We plan to extend to:

| Platform | Planned Approach | Status |
|----------|-----------------|--------|
| **Mobile (iOS/Android)** | Appium / browser-use mobile integration | Planned |
| **API Testing** | HTTP request tools for the AI agent | Planned |
| **Desktop (Electron, native)** | Playwright Electron / OS-level automation | Under investigation |

The goal is a unified test framework where the same Explore → Replay workflow works across Web, Mobile, and API — write once, test everywhere.

---

## CLI Commands

```bash
skiritai run <case_dir>               # Run a test case
skiritai serve [--host] [--port]       # Start web server
skiritai list [cases_root]            # List available cases
skiritai browser status [case_dir]    # Check persistent browser session
skiritai browser cleanup [case_dir]   # Kill orphan browser process
```

## Tool Set

14 Playwright tools available to the AI agent:

| Tool            | Description                           |
|-----------------|---------------------------------------|
| `navigate`      | Navigate to URL                       |
| `click`         | Click element                         |
| `click_force`   | Force click (for hidden elements)     |
| `fill`          | Fill input field                      |
| `type_text`     | Type character by character           |
| `focus`         | Focus on element                      |
| `get_text`      | Get element text content              |
| `get_page_info` | Get page title, URL, and text summary |
| `wait_for`      | Wait for element to appear            |
| `scroll`        | Scroll page                           |
| `eval_js`       | Execute JavaScript                    |
| `select_option` | Select dropdown option                |
| `hover`         | Hover over element                    |
| `screenshot`    | Capture page screenshot               |

## Execution Modes

Control how each step executes via `ai.action()` or the `@step_mode` decorator:

| Mode             | Behavior                                   | Use Case                     |
|------------------|--------------------------------------------|------------------------------|
| `auto` (default) | Replay if script exists, otherwise explore | Most steps                   |
| `explore`        | Always use AI, overwrite existing script   | New features, re-exploration |
| `replay`         | Always replay, error if no script          | CI/CD regression             |

```python
# Via decorator
@step_mode("explore")
async def my_step(self, ai):
    await ai.action("...")


# Via parameter (overrides decorator)
await ai.action("...", mode="replay")
```

<div align="center">

---

### Author

**Joe Shen**

[![GitHub](https://img.shields.io/badge/GitHub-@Ktovoz-181717?logo=github&logoColor=white)](https://github.com/Ktovoz)

</div>

<div align="center">

---

### License

[![MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

### Contributing

[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-2EA44F?logo=github&logoColor=white)](https://github.com/Ktovoz/Skiritai/pulls)

Contributions, issues, and feature requests are welcome!

</div>
