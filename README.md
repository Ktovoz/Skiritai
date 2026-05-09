<div align="center">

# Skiritai

**AI-Powered Test Automation Agent**

<em>Named after the Skiritai — Sparta's elite reconnaissance troops who scouted the path ahead of the main army.</em>

<br>

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19+-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## What is Skiritai?

Skiritai is an AI-driven test automation framework that **scouts automation paths before executing them**.

Like the ancient Skiritai who reconnoitered the terrain before the Spartan army advanced, Skiritai's agent first **explores** the target application — navigating pages, discovering UI elements, and figuring out the correct sequence of actions — then **generates replayable scripts** that can execute the same path at 30x speed without any AI inference.

```
Explore Mode (Scout the path)
  AI Agent → analyze page → decide actions → generate scripts
         ↓
Replay Mode (Execute the proven path)
  Script → direct execution → no AI needed → 30x faster
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Explore → Replay Loop** | AI explores and generates scripts on first run; replays them instantly on subsequent runs |
| **30x Performance** | Replay mode skips AI inference entirely — 74s → 2.5s |
| **Python-native Cases** | Define test cases as Python classes with `@step_mode` decorators |
| **Auto-Solidification** | Successful explorations are automatically saved as replayable scripts |
| **Multi-level Fallback** | `fill` → `click_force` → `eval_js` for resilient element interaction |
| **Real-time Monitoring** | WebSocket-based live execution logs and event streaming |
| **Flexible LLM** | Supports OpenAI, Anthropic, Qwen, and any compatible API |
| **Web UI** | React + TypeScript dashboard for managing and monitoring test cases |

## How It Works

```python
from app.engine.base_case import BaseCase, step_mode

class SearchTest(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_site(self, ai):
        await ai.action("Navigate to https://example.com")

    @step_mode("explore")  # Force AI exploration for this step
    async def search(self, ai):
        await ai.action("Search for 'automation testing'")

    async def verify(self, ai):
        await ai.action("Verify search results are displayed")
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

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- An LLM API key (OpenAI / Anthropic / compatible provider)

### 1. Install Backend

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure

```bash
# backend/.env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. Run

```bash
cd backend
python -c "
import asyncio
from app.engine.py_case_runner import run_case
from pathlib import Path

asyncio.run(run_case(Path('../cases/baidu_search')))
"
```

### 4. (Optional) Start Web UI

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| AI Engine | LangGraph + LangChain (ReAct Agent) |
| LLM | OpenAI / Anthropic / Qwen / any compatible API |
| Browser Automation | Playwright |
| Backend | FastAPI (async) |
| Frontend | React + TypeScript + Vite |
| Storage | File-based (scripts, results, reports) |

## Project Structure

```
Skiritai/
├── backend/
│   ├── app/
│   │   ├── engine/
│   │   │   ├── agent_loop.py      # LangGraph ReAct Agent
│   │   │   ├── ai_context.py      # Explore/Replay execution context
│   │   │   ├── base_case.py       # Test case base class
│   │   │   ├── py_case_runner.py  # Python case runner
│   │   │   ├── tools.py           # Playwright tool set (14 tools)
│   │   │   └── browser.py         # Browser lifecycle management
│   │   ├── routers/
│   │   │   ├── cases.py           # REST API for cases
│   │   │   └── ws.py              # WebSocket real-time events
│   │   └── main.py
│   └── tests/
├── cases/                          # Test case definitions
│   ├── baidu_search/
│   └── playwright_docs/
├── frontend/                       # Web dashboard (React + TS)
├── LICENSE
└── README.md
```

## Tool Set

14 Playwright tools available to the AI agent:

| Tool | Description |
|------|-------------|
| `navigate` | Navigate to URL |
| `click` | Click element |
| `click_force` | Force click (for hidden elements) |
| `fill` | Fill input field |
| `type_text` | Type character by character |
| `focus` | Focus on element |
| `get_text` | Get element text content |
| `get_page_info` | Get page title, URL, and text summary |
| `wait_for` | Wait for element to appear |
| `scroll` | Scroll page |
| `eval_js` | Execute JavaScript |
| `select_option` | Select dropdown option |
| `hover` | Hover over element |
| `screenshot` | Capture page screenshot |

## Execution Modes

Control how each step executes via `ai.action()` or the `@step_mode` decorator:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `auto` (default) | Replay if script exists, otherwise explore | Most steps |
| `explore` | Always use AI, overwrite existing script | New features, re-exploration |
| `replay` | Always replay, error if no script | CI/CD regression |

```python
# Via decorator
@step_mode("explore")
async def my_step(self, ai):
    await ai.action("...")

# Via parameter (overrides decorator)
await ai.action("...", mode="replay")
```

## Author

**Joe Shen** (Ktovoz)
- GitHub: [@Ktovoz](https://github.com/Ktovoz)

## License

[MIT](LICENSE)

## Contributing

Issues and Pull Requests are welcome!
