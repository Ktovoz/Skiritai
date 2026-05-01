# TestAgent

**AI-powered test automation framework** — let AI explore test paths and auto-generate replayable test scripts

[English](README.md) | [中文](README_zh.md)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-green.svg)](https://playwright.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-orange.svg)](https://langchain-ai.github.io/langgraph/)

---

## Key Features

### Explore → Replay Loop

The core concept: **"explore first, replay later"**:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Explore** | AI analyzes the page, decides actions, generates replay scripts | First run, new feature verification |
| **Replay** | Executes saved scripts directly, no AI reasoning | Regression testing, CI/CD integration |

### How It Works

`ai.action()` accepts an optional `mode` parameter to control execution:

```python
await ai.action("Navigate to Baidu")                    # auto (default)
await ai.action("Navigate to Baidu", mode="auto")       # same as above
await ai.action("Navigate to Baidu", mode="explore")    # force AI exploration
await ai.action("Navigate to Baidu", mode="replay")     # force replay
```

| Mode | Behavior |
|------|----------|
| `auto` (default) | Replay if script exists, otherwise explore |
| `explore` | Always use AI, overwrite existing script |
| `replay` | Always replay, error if no script exists |

**Default flow (`auto` mode):**

```
First run:
  ai.action("Navigate to Baidu")  →  no script  →  AI explores  →  generates scripts/open_baidu.py

Second run:
  ai.action("Navigate to Baidu")  →  script exists  →  replay directly (no AI)
```

**Force re-explore** when replay result is unsatisfactory:

```python
# Re-explore this step even if a replay script already exists
await ai.action("Navigate to Baidu", mode="explore")
```

### 30x Performance Boost

Replay mode skips AI inference entirely:

```
Explore: 74.67s  (AI reasoning + tool calls + script generation)
Replay:   2.47s  (direct script execution)
Speedup: 30.3x
```

### Python-native Test Cases

Define test cases as Python classes, with per-step mode config in `case.yaml`:

```python
# cases/baidu_search/case.py
from app.engine.base_case import BaseCase

class BaiduSearchCase(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_baidu(self, ai):
        await ai.action("Navigate to Baidu homepage")

    async def search_keyword(self, ai):
        await ai.action("Search for 'Playwright automation testing'")

    async def verify_results(self, ai):
        await ai.action("Verify search results loaded")
```

```yaml
# cases/baidu_search/case.yaml
name: BaiduSearchCase
description: Baidu search test case
steps:
  open_baidu:
    mode: auto          # auto / explore / replay
  search_keyword:
    mode: explore       # force this step to always explore
  verify_results:
    mode: auto
```

The `mode` in `case.yaml` is the default for each step. It can still be overridden in code:

```python
await ai.action("Navigate to Baidu", mode="explore")  # overrides YAML config
```

---

## Tech Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| **AI Engine** | LangGraph + LangChain | ReAct Agent pattern, autonomous tool calling |
| **LLM** | OpenAI / Qwen / any compatible API | Flexible model switching |
| **Browser Automation** | Playwright | Chrome, Firefox, Safari support |
| **Backend** | FastAPI | High-performance async API |
| **Frontend** | React + TypeScript + Vite | Modern UI |
| **Storage** | File system | Scripts, results, reports all file-based |

---

## Project Structure

```
backend/
├── app/
│   ├── engine/
│   │   ├── agent_loop.py      # LangGraph ReAct Agent
│   │   ├── ai_context.py      # AI action context (explore/replay)
│   │   ├── base_case.py       # Test case base class
│   │   ├── py_case_runner.py  # Python case runner
│   │   ├── tools.py           # Playwright tool set
│   │   └── browser.py         # Browser configuration
│   ├── routers/
│   │   ├── cases.py           # Case API
│   │   └── ws.py              # WebSocket real-time push
│   └── main.py
└── tests/
    ├── test_py_case.py
    └── test_replay_vs_explore.py
cases/
├── baidu_search/
│   ├── case.py                # Test case definition
│   ├── case.yaml              # Per-step mode config
│   └── scripts/               # Replay scripts
└── playwright_docs/
frontend/
LICENSE
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

```bash
# backend/.env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. Run a Test Case

```bash
cd backend
python -c "
import asyncio
from app.engine.py_case_runner import run_case
from pathlib import Path

asyncio.run(run_case(Path('../cases/baidu_search')))
"
```

---

## Tools

TestAgent provides 13 Playwright tools:

| Tool | Description |
|------|-------------|
| `navigate` | Navigate to URL |
| `click` | Click element |
| `click_force` | Force click (hidden elements) |
| `fill` | Fill input field |
| `type_text` | Type character by character |
| `focus` | Focus on element |
| `get_text` | Get element text |
| `get_page_info` | Get page title, URL and text summary |
| `wait_for` | Wait for element to appear |
| `scroll` | Scroll page |
| `eval_js` | Execute JavaScript |
| `select_option` | Select dropdown option |
| `hover` | Hover over element |

---

## Core Advantages

### 1. Intelligent Exploration

AI Agent autonomously analyzes page structure and decides the best action path:

```python
await ai.action("Type keyword in search box and search")
# AI may call: fill -> click, or eval_js, depending on page state
```

### 2. Auto-Solidification

After successful exploration, a replay script is auto-generated for future reuse:

```
First run:  explore -> generates scripts/search_keyword.py
Next run:   replay  -> directly executes scripts/search_keyword.py
```

### 3. Reliable

- **Locator API**: Uses Playwright's auto-wait mechanism
- **Multi-level fallback**: fill -> click_force -> eval_js
- **Error recovery**: Single step failure doesn't affect other steps

### 4. Easy to Extend

Add new test cases by inheriting `BaseCase`:

```python
from app.engine.base_case import BaseCase

class MyTestCase(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def my_step(self, ai):
        await ai.action("Execute custom operation")
```

---

## Benchmark: Explore vs Replay

| Metric | Explore | Replay | Improvement |
|--------|---------|--------|-------------|
| Execution time | 74.67s | 2.47s | **30.3x** |
| Time saved | - | 72.20s | - |
| AI calls | Yes | No | - |
| Scripts generated | 3 scripts | Direct execution | - |

**Explore mode flow:**
```
[Step] open_baidu (explore)     -> 20s  -> generates scripts/open_baidu.py
[Step] search_keyword (explore) -> 30s  -> generates scripts/search_keyword.py
[Step] verify_results (explore) -> 24s  -> generates scripts/verify_results.py
```

**Replay mode flow:**
```
[Step] open_baidu (replay)     -> 0.8s -> direct script execution
[Step] search_keyword (replay) -> 0.8s -> direct script execution
[Step] verify_results (replay) -> 0.8s -> direct script execution
```

---

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!
