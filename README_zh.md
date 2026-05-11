<div align="center">

# Skiritai

**AI 驱动的测试自动化智能体**

<em>以古斯巴达精锐侦察部队「斯基里泰」命名 — 他们总是在大军推进前，先行侦察出可行的路径。</em>

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

## Skiritai 是什么？

Skiritai 是一个 AI 驱动的浏览器测试自动化框架，核心理念是 **先侦察自动化路径，再执行**。

就像古斯巴达的斯基里泰部队在大军推进前先行侦察地形，Skiritai 的智能体会先**探索**目标应用 — 导航页面、发现 UI
元素、确定正确的操作序列 — 然后**生成可回放的脚本**，后续执行时无需 AI 推理，速度提升 30 倍。

```
探索模式（侦察路径）
  AI Agent → 分析页面 → 决策操作 → 生成脚本
         ↓
回放模式（执行已验证的路径）
  脚本 → 直接执行 → 无需 AI → 速度提升 30x
```

## 核心特性

| 特性              | 说明                                          |
|-----------------|---------------------------------------------|
| **探索 → 回放闭环**   | 首次运行 AI 探索并生成脚本，后续运行直接回放                    |
| **30 倍性能提升**    | 回放模式跳过 AI 推理 — 74s → 2.5s                   |
| **Flow API**      | 函数式、无需继承的 API — `async with flow() as ai:`                  |
| **YAML 用例**     | 用 YAML 定义测试步骤，通过 CLI 或 `run_yaml_case()` 运行          |
| **Python 原生用例** | 用 Python 类定义测试用例，`@step_mode` 装饰器控制模式       |
| **自动固化**        | 探索成功后自动生成可回放脚本                              |
| **多重降级策略**      | `fill` → `click_force` → `eval_js`，确保元素交互稳定 |
| **灵活的 LLM**     | 支持 OpenAI、Anthropic、Qwen 及任意兼容 API          |
| **可选 Web 界面**   | FastAPI 后端提供 REST + WebSocket 接口，支持外部前端集成   |
| **可视化报告**     | Vue 3 + Ant Design 构建的独立 HTML 报告，包含截图、断言、步骤详情 |
| **CLI 工具**      | `skiritai run/serve/list/browser` 命令行操作     |

## 工作原理

```python
from skiritai import BaseCase, step_mode


class SearchTest(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_site(self):
        await self.ai.action("导航到 https://example.com")

    @step_mode("explore")  # 强制探索模式
    async def search(self):
        await self.ai.action("搜索 '自动化测试'")

    async def verify(self):
        await self.ai.action("验证搜索结果已展示")
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

### Flow API（函数式，无需继承）

```python
from skiritai import flow

async with flow() as ai:
    await ai.action("导航到 https://example.com")
    await ai.screenshot("homepage")
    await ai.verify("页面标题包含 'Example'")
```

`flow()` 是一个函数式上下文管理器 — 无需子类、无需装饰器。直接使用 `ai.action()`、`ai.verify()`、`ai.screenshot()`、`ai.analyze_page()` 和 `ai.get_page_info()`。

### YAML 用例（零代码）

```yaml
# case.yaml
name: 搜索测试
steps:
  - action: 打开 https://www.baidu.com
  - action: 搜索 "Playwright"
  - verify: 搜索结果已展示
  - screenshot: result
```

```bash
skiritai run examples/baidu_yaml
```

YAML 用例非常适合不想编写 Python 代码的 QA 团队。支持 `action`、`verify`、`screenshot`、`analyze`、`page_info` 步骤类型，以及每步级别的 `on_failure: skip | abort` 策略。

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
skiritai run examples/tutorial/minimal

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
│   ├── flow.py                # 函数式、无需继承的 API
│   ├── yaml_runner.py         # YAML 用例加载与运行器
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

report/                        # 可视化报告项目（Vue 3 + Ant Design）
├── src/                       #   组件：ReportHeader、SummaryBar、StepCard、ScreenshotViewer
├── dist/                      #   构建产物（单文件 HTML，由 _render_html 注入数据）
└── package.json               #   skiritai-report

examples/                      # 示例测试用例
├── tutorial/                  # 教学示例（学习框架特性）
│   ├── minimal/               #   纯 Playwright，无需 AI
│   ├── step_modes/            #   auto/explore/replay 三种执行模式
│   ├── failure_policies/      #   ABORT/SKIP/RETRY 失败策略
│   ├── hooks_demo/            #   before_step/after_step/on_step_error 钩子
│   └── context_demo/          #   self.ctx 跨步骤上下文共享
├── baidu_search/              # [初次尝试] 完整端到端 AI 驱动测试 + 回放脚本
└── ktovoz_blog/               # [进阶] 11 步长程博客测试

tests/                         # 框架测试
├── unit/
├── functional/
├── acceptance/
└── e2e/
```

## 示例

示例分为三个层级：

### 新式编写方式（无需 BaseCase）

| 示例 | 说明 |
|---|---|
| `flow_demo/` | 函数式 Flow API — `async with flow() as ai:` 风格，无需继承 |
| `baidu_yaml/` | YAML 定义的测试用例 — 完全用 YAML 编写测试 |

### 教学（学习框架特性）

| 示例 | 教学内容 |
|---|---|
| `minimal/` | BaseCase 基本结构 — 纯 Playwright，无需 LLM |
| `step_modes/` | `auto` / `explore` / `replay` 三种执行模式 |
| `failure_policies/` | `@on_failure(SKIP)` / `@on_failure(RETRY)` 错误处理 |
| `hooks_demo/` | `before_step` / `after_step` / `on_step_error` 生命周期钩子 |
| `context_demo/` | `self.ctx.store` 跨步骤数据共享 |

### 初次尝试（真实端到端场景）

| 示例 | 说明 |
|---|---|
| `baidu_search/` | 完整 E2E：打开百度 → 搜索 → 验证结果。展示真实场景下的探索→回放闭环。 |

### 进阶（长程测试）

| 示例 | 说明 |
|---|---|
| `ktovoz_blog/` | 11 步博客测试：首页、文章、标签、关于、页脚、搜索、总结。展示框架处理复杂多步骤场景的能力。 |

```bash
# Flow API — 函数式风格，无需继承
python examples/flow_demo/demo.py

# YAML 用例 — 零 Python 代码
skiritai run examples/baidu_yaml

# 从教学示例开始（无需 AI）
skiritai run examples/tutorial/minimal

# 尝试真实场景（需要配置 LLM）
skiritai run examples/baidu_search

# 进阶长程测试
skiritai run examples/ktovoz_blog
```

## 路线图

### 视觉感知层

当前 AI 探索依赖 DOM 分析和 CSS 选择器。下一步将引入**视觉感知**能力 — 智能体将像人类测试员一样"看见"页面：

- **基于视觉的 AI 探索** — 通过截图理解页面，识别 UI 元素的视觉特征，支持 canvas/WebGL 等无 DOM 可访问的界面
- **多模态模型支持** — 接入视觉语言模型（GPT-4o、Claude 3.5 Sonnet、Gemini）和原生多模态模型，实现更丰富的页面理解
- **视觉回归检测** — 跨运行截图对比，自动发现非预期的 UI 变化

### 多端与跨端测试

Skiritai 目前仅支持 **Web** 端（Playwright/Chromium），未来将扩展到：

| 平台 | 计划方案 | 状态 |
|------|---------|------|
| **移动端（iOS/Android）** | Appium / browser-use mobile 集成 | 规划中 |
| **API 测试** | AI 智能体可用的 HTTP 请求工具 | 规划中 |
| **桌面端（Electron、原生应用）** | Playwright Electron / 系统级自动化 | 调研中 |

目标是构建统一的测试框架，相同的「探索 → 回放」工作流在 Web、移动端、API 上通用 — 一次编写，到处测试。

---

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

| 工具              | 说明               |
|-----------------|------------------|
| `navigate`      | 导航到 URL          |
| `click`         | 点击元素             |
| `click_force`   | 强制点击（隐藏元素）       |
| `fill`          | 填写输入框            |
| `type_text`     | 逐字符输入            |
| `focus`         | 聚焦元素             |
| `get_text`      | 获取元素文本           |
| `get_page_info` | 获取页面标题、URL 和文本摘要 |
| `wait_for`      | 等待元素出现           |
| `scroll`        | 滚动页面             |
| `eval_js`       | 执行 JavaScript    |
| `select_option` | 选择下拉选项           |
| `hover`         | 鼠标悬停             |
| `screenshot`    | 截取页面截图           |

## 执行模式

通过 `ai.action()` 或 `@step_mode` 装饰器控制每个步骤的执行方式：

| 模式         | 行为               | 适用场景       |
|------------|------------------|------------|
| `auto`（默认） | 有脚本则回放，否则探索      | 大多数步骤      |
| `explore`  | 始终用 AI 探索，覆盖已有脚本 | 新功能、重新探索   |
| `replay`   | 始终回放，无脚本则报错      | CI/CD 回归测试 |

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

<div align="center">

---

### 许可证

[![MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

### 贡献

[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-2EA44F?logo=github&logoColor=white)](https://github.com/Ktovoz/Skiritai/pulls)

欢迎提交 Issue、Feature Request 和 Pull Request！

</div>
