<div align="center">

# Skiritai

**AI 驱动的测试自动化智能体**

<em>以古斯巴达精锐侦察部队「斯基里泰」命名 — 他们总是在大军推进前，先行侦察出可行的路径。</em>

<br>

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## Skiritai 是什么？

Skiritai 是一个 AI 驱动的浏览器测试自动化框架，核心理念是 **先侦察自动化路径，再执行**。

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
| **灵活的 LLM** | 支持 OpenAI、Anthropic、Qwen 及任意兼容 API |
| **可选 Web 界面** | FastAPI 后端提供 REST + WebSocket 接口，支持外部前端集成 |
| **CLI 工具** | `skiritai run/serve/list/browser` 命令行操作 |

## 工作原理

```python
from skiritai import BaseCase, step_mode

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

### 1. 安装

```bash
pip install skiritai
playwright install chromium
```

### 2. 配置

```bash
# .env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### 3. 运行

```bash
# 运行示例用例
skiritai run examples/minimal

# 列出可用用例
skiritai list examples/
```

或以编程方式调用：

```python
import asyncio
from pathlib import Path
from skiritai import run_case

report = asyncio.run(run_case(Path("examples/minimal")))
print(report)
```

### 4.（可选）启动 Web 服务

```bash
pip install skiritai[web]
skiritai serve --host 0.0.0.0 --port 8000
```

## 项目结构

```
skiritai/
├── core/                      # 核心引擎（始终安装）
│   ├── agent_loop.py          # LangGraph ReAct Agent
│   ├── ai_context.py          # 探索/回放执行上下文
│   ├── base_case.py           # 测试用例基类
│   ├── runner.py              # 用例发现与执行
│   ├── tools.py               # Playwright 工具集（14 个工具）
│   ├── browser.py             # 浏览器生命周期管理
│   └── ...
├── llm/                       # LLM 提供者抽象层
│   ├── openai_provider.py
│   └── anthropic_provider.py
├── events/                    # 事件总线
├── web/                       # [可选] FastAPI 服务（pip install skiritai[web]）
│   ├── app.py                 # 应用工厂
│   ├── routers/               # REST + WebSocket 端点
│   └── ws_manager.py          # 事件 → WebSocket 桥接
└── cli.py                     # CLI 入口

examples/                      # 示例测试用例
├── minimal/                   # 纯 Playwright，无需 AI
├── baidu_search/              # AI 驱动 + 回放脚本
└── playwright_docs/           # 探索示例

tests/                         # 框架测试
├── unit/
├── functional/
├── acceptance/
└── e2e/
```

## CLI 命令

```bash
skiritai run <case_dir>               # 运行测试用例
skiritai serve [--host] [--port]       # 启动 Web 服务
skiritai list [cases_root]            # 列出可用用例
skiritai browser status [case_dir]    # 查看持久浏览器会话状态
skiritai browser cleanup [case_dir]   # 终止孤立浏览器进程
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

<div align="center">

---

### 作者

**Joe Shen**

[![GitHub](https://img.shields.io/badge/GitHub-@Ktovoz-181717?logo=github&logoColor=white)](https://github.com/Ktovoz)

</div>

## 许可证

[MIT](LICENSE)

<div align="center">

欢迎提交 Issue 和 Pull Request！

</div>
