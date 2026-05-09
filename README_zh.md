<div align="center">

# Skiritai

**AI 驱动的测试自动化智能体**

<em>以古斯巴达精锐侦察部队「斯基里泰」命名 — 他们总是在大军推进前，先行侦察出可行的路径。</em>

<br>

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19+-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## Skiritai 是什么？

Skiritai 是一个 AI 驱动的测试自动化框架，核心理念是 **先侦察自动化路径，再执行**。

就像古斯巴达的斯基里泰部队在大军推进前先行侦察地形，Skiritai 的智能体会先**探索**目标应用 — 导航页面、发现 UI 元素、确定正确的操作序列 — 然后**生成可回放的脚本**，后续执行时无需 AI 推理，速度提升 30 倍。

```
探索模式（侦察路径）
  AI Agent → 分析页面 → 决策操作 → 生成脚本
         ↓
回放模式（执行已验证的路径）
  脚本 → 直接执行 → 无需 AI → 速度提升 30x
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **探索 → 回放闭环** | 首次运行 AI 探索并生成脚本，后续运行直接回放 |
| **30 倍性能提升** | 回放模式跳过 AI 推理 — 74s → 2.5s |
| **Python 原生用例** | 用 Python 类定义测试用例，`@step_mode` 装饰器控制模式 |
| **自动固化** | 探索成功后自动生成可回放脚本 |
| **多重降级策略** | `fill` → `click_force` → `eval_js`，确保元素交互稳定 |
| **实时监控** | WebSocket 实时推送执行日志和事件 |
| **灵活的 LLM** | 支持 OpenAI、Anthropic、Qwen 及任意兼容 API |
| **Web 管理界面** | React + TypeScript 仪表盘，管理和监控测试用例 |

## 工作原理

```python
from app.engine.base_case import BaseCase, step_mode

class SearchTest(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_site(self, ai):
        await ai.action("导航到 https://example.com")

    @step_mode("explore")  # 强制探索模式
    async def search(self, ai):
        await ai.action("搜索 '自动化测试'")

    async def verify(self, ai):
        await ai.action("验证搜索结果已展示")
```

**首次运行** — AI 探索每个步骤，生成脚本：

```
[Step] open_site   (explore)  → 20s  → scripts/open_site.py   ✓
[Step] search      (explore)  → 30s  → scripts/search.py      ✓
[Step] verify      (explore)  → 24s  → scripts/verify.py      ✓
总计: 74s
```

**再次运行** — 直接回放脚本，无需 AI：

```
[Step] open_site   (replay)   → 0.8s → 直接执行               ✓
[Step] search      (replay)   → 0.8s → 直接执行               ✓
[Step] verify      (replay)   → 0.8s → 直接执行               ✓
总计: 2.5s
```

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+（前端需要）
- 一个 LLM API Key（OpenAI / Anthropic / 兼容服务商）

### 1. 安装后端

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

```bash
# backend/.env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. 运行测试

```bash
cd backend
python -c "
import asyncio
from app.engine.py_case_runner import run_case
from pathlib import Path

asyncio.run(run_case(Path('../cases/baidu_search')))
"
```

### 4.（可选）启动 Web 界面

```bash
cd frontend
npm install
npm run dev
```

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 引擎 | LangGraph + LangChain（ReAct Agent 模式） |
| LLM | OpenAI / Anthropic / Qwen / 任意兼容 API |
| 浏览器自动化 | Playwright |
| 后端框架 | FastAPI（异步） |
| 前端 | React + TypeScript + Vite |
| 数据存储 | 文件系统（脚本、结果、报告） |

## 项目结构

```
Skiritai/
├── backend/
│   ├── app/
│   │   ├── engine/
│   │   │   ├── agent_loop.py      # LangGraph ReAct Agent
│   │   │   ├── ai_context.py      # 探索/回放执行上下文
│   │   │   ├── base_case.py       # 测试用例基类
│   │   │   ├── py_case_runner.py  # Python 用例运行器
│   │   │   ├── tools.py           # Playwright 工具集（14 个工具）
│   │   │   └── browser.py         # 浏览器生命周期管理
│   │   ├── routers/
│   │   │   ├── cases.py           # REST API
│   │   │   └── ws.py              # WebSocket 实时事件
│   │   └── main.py
│   └── tests/
├── cases/                          # 测试用例定义
│   ├── baidu_search/
│   └── playwright_docs/
├── frontend/                       # Web 仪表盘（React + TS）
├── LICENSE
└── README.md
```

## 工具集

AI 智能体可使用的 14 个 Playwright 工具：

| 工具 | 说明 |
|------|------|
| `navigate` | 导航到 URL |
| `click` | 点击元素 |
| `click_force` | 强制点击（隐藏元素） |
| `fill` | 填写输入框 |
| `type_text` | 逐字符输入 |
| `focus` | 聚焦元素 |
| `get_text` | 获取元素文本 |
| `get_page_info` | 获取页面标题、URL 和文本摘要 |
| `wait_for` | 等待元素出现 |
| `scroll` | 滚动页面 |
| `eval_js` | 执行 JavaScript |
| `select_option` | 选择下拉选项 |
| `hover` | 鼠标悬停 |
| `screenshot` | 截取页面截图 |

## 执行模式

通过 `ai.action()` 或 `@step_mode` 装饰器控制每个步骤的执行方式：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `auto`（默认） | 有脚本则回放，否则探索 | 大多数步骤 |
| `explore` | 始终用 AI 探索，覆盖已有脚本 | 新功能、重新探索 |
| `replay` | 始终回放，无脚本则报错 | CI/CD 回归测试 |

```python
# 通过装饰器
@step_mode("explore")
async def my_step(self, ai):
    await ai.action("...")

# 通过参数（覆盖装饰器）
await ai.action("...", mode="replay")
```

## 作者

**Joe Shen**（Ktovoz）
- GitHub: [@Ktovoz](https://github.com/Ktovoz)

## 许可证

[MIT](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request！
