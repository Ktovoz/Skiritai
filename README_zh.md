# TestAgent

**AI 驱动的测试自动化框架** — 让 AI 探索测试路径，自动生成可回放的测试脚本

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-green.svg)](https://playwright.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-orange.svg)](https://langchain-ai.github.io/langgraph/)

---

## 核心特性

### 探索 → 回放 闭环

TestAgent 的核心理念是 **"先探索，后回放"**：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| **探索模式** | AI 自主分析页面，决定操作，生成回放脚本 | 首次执行、新功能验证 |
| **回放模式** | 直接执行已生成的脚本，无 AI 推理 | 回归测试、CI/CD 集成 |

### 30x 性能提升

回放模式直接执行脚本，跳过 AI 推理环节：

```
探索模式: 74.67s  (AI 推理 + 工具调用 + 脚本生成)
回放模式:  2.47s  (直接执行脚本)
加速比:   30.3x
```

### Python 原生用例

用 Python 类定义测试用例，告别 YAML 配置：

```python
from app.engine.base_case import BaseCase

class BaiduSearchCase(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_baidu(self, ai):
        await ai.action("导航到百度首页")

    async def search_keyword(self, ai):
        await ai.action("搜索 'Playwright 自动化测试'")

    async def verify_results(self, ai):
        await ai.action("验证搜索结果")
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **AI 引擎** | LangGraph + LangChain | ReAct Agent 模式，自主决策工具调用 |
| **LLM** | OpenAI / Qwen / 任意兼容 API | 灵活切换模型 |
| **浏览器自动化** | Playwright | 支持 Chrome、Firefox、Safari |
| **后端框架** | FastAPI | 高性能异步 API |
| **前端** | React + TypeScript + Vite | 现代化 UI |
| **数据存储** | 文件系统 | 脚本、结果、报告全部基于文件 |

---

## 项目结构

```
TestAgent/
├── backend/
│   ├── app/
│   │   ├── engine/
│   │   │   ├── agent_loop.py      # LangGraph ReAct Agent
│   │   │   ├── ai_context.py      # AI 动作上下文（探索/回放）
│   │   │   ├── base_case.py       # 测试用例基类
│   │   │   ├── py_case_runner.py  # Python 用例运行器
│   │   │   ├── tools.py           # Playwright 工具集
│   │   │   └── browser.py         # 浏览器配置
│   │   ├── routers/
│   │   │   ├── cases.py           # Case API
│   │   │   └── ws.py              # WebSocket 实时推送
│   │   └── main.py
│   └── tests/
│       ├── test_py_case.py        # Python 用例测试
│       └── test_replay_vs_explore.py  # 探索 vs 回放对比
├── cases/
│   ├── baidu_search/
│   │   ├── case.py                # 测试用例定义
│   │   ├── scripts/               # 回放脚本
│   │   └── results/               # 执行结果
│   └── playwright_docs/
├── frontend/
└── test_report.html               # 测试对比报告
```

---

## 快速开始

### 1. 安装依赖

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

### 3. 运行测试用例

```bash
cd backend
python -c "
import asyncio
from app.engine.py_case_runner import run_case
from pathlib import Path

asyncio.run(run_case(Path('../cases/baidu_search')))
"
```

### 4. 查看测试报告

```bash
open test_report.html
```

---

## 工具集

TestAgent 提供 12 个 Playwright 工具，覆盖常见操作：

| 工具 | 说明 |
|------|------|
| `navigate` | 导航到 URL |
| `click` | 点击元素 |
| `click_force` | 强制点击（隐藏元素） |
| `fill` | 填写输入框 |
| `type_text` | 逐字符输入 |
| `focus` | 聚焦元素 |
| `get_text` | 获取元素文本 |
| `get_page_info` | 获取页面信息 |
| `wait_for` | 等待元素出现 |
| `scroll` | 滚动页面 |
| `eval_js` | 执行 JavaScript |
| `select_option` | 选择下拉选项 |
| `hover` | 鼠标悬停 |

---

## 核心优势

### 1. 智能探索

AI Agent 自主分析页面结构，决定最佳操作路径：

```python
# AI 会自动选择合适的工具
await ai.action("在搜索框中输入关键词并搜索")
# AI 可能调用: fill → click，或 eval_js，取决于页面状态
```

### 2. 自动固化

探索成功后自动生成回放脚本，下次执行直接复用：

```
首次执行: explore → 生成 scripts/search_keyword.py
再次执行: replay → 直接执行 scripts/search_keyword.py
```

### 3. 稳定可靠

- **Locator API**: 使用 Playwright 的自动等待机制
- **多重降级**: fill 失败 → click_force → eval_js
- **错误恢复**: 单步失败不影响其他步骤

### 4. 易于扩展

添加新的测试用例只需继承 `BaseCase`：

```python
from app.engine.base_case import BaseCase

class MyTestCase(BaseCase):
    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def my_step(self, ai):
        await ai.action("执行自定义操作")
```

---

## 测试报告

### 探索模式 vs 回放模式 对比

| 指标 | 探索模式 | 回放模式 | 提升 |
|------|----------|----------|------|
| 执行时间 | 74.67s | 2.47s | **30.3x** |
| 节省时间 | - | 72.20s | - |
| AI 调用 | 有 | 无 | - |
| 脚本生成 | 生成 3 个脚本 | 直接执行 | - |

### 测试详情

**探索模式执行流程：**
```
[Step] open_baidu (explore)    → 20s  → 生成 scripts/open_baidu.py
[Step] search_keyword (explore) → 30s  → 生成 scripts/search_keyword.py
[Step] verify_results (explore) → 24s  → 生成 scripts/verify_results.py
```

**回放模式执行流程：**
```
[Step] open_baidu (replay)     → 0.8s → 直接执行脚本
[Step] search_keyword (replay) → 0.8s → 直接执行脚本
[Step] verify_results (replay) → 0.8s → 直接执行脚本
```

### 生成的回放脚本示例

```python
# scripts/search_keyword.py
async def run(page, context):
    await page.evaluate("document.getElementById('kw').value = 'Playwright 自动化测试'; document.getElementById('su').click();")
```

### 测试报告文件

- **HTML 报告**: `test_report.html`
- **测试代码**: `backend/tests/test_replay_vs_explore.py`
- **探索用例**: `cases/baidu_search_explore/case.py`
- **回放用例**: `cases/baidu_search_replay/case.py`

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
