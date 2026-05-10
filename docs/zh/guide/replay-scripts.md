# 回放脚本

探索完成后，AI Agent 生成独立的 Python 脚本，以 ~30 倍速度回放相同的操作，零 LLM 开销。

## 工作原理

1. **探索阶段** — AI Agent 分析页面，调用工具（click、fill、navigate 等），记录每一步操作
2. **脚本生成** — 工具调用历史被编译为独立的 `.py` 文件，使用直接的 Playwright API 调用
3. **回放阶段** — 生成的脚本直接在 Playwright 上执行，无需 AI 参与

## 脚本结构

生成的脚本遵循标准模式：

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

脚本保存在 `<case_dir>/scripts/<step_name>.py`。

## 运行脚本

### 独立运行

```bash
python scripts/my_step.py
```

### 导入运行

```python
import importlib.util
spec = importlib.util.spec_from_file_location("script", "scripts/my_step.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
await module.run(page, context)
```

## 只读工具过滤

回放脚本仅包含**操作**工具（navigate、click、fill 等）。**感知**和只读工具被排除：

| 排除的工具 | 原因 |
|---------------|--------|
| `page_perceive` | 只读 DOM 分析，回放时不需要 |
| `find_element` | 只读搜索，选择器已确定 |
| `get_page_info` | 只读元数据 |
| `get_text` | 只读内容提取 |
| `response` | 最终摘要，非操作 |

## 脚本管理 API

### 列出脚本

```bash
GET /api/cases/{id}/scripts
```

返回用例的所有回放脚本及其内容。

### 获取脚本内容

```bash
GET /api/cases/{id}/scripts/{step}
```

返回特定步骤的完整脚本内容。

### 编辑脚本

```bash
PUT /api/cases/{id}/scripts/{step}
Content-Type: application/json

{"content": "async def run(page, context):\n    await page.goto('...')"}
```

用于微调生成的脚本，无需重新探索。

### 固化脚本

```bash
POST /api/cases/{id}/scripts/{step}/solidify
```

创建 `.solidified` 标记文件。固化的脚本被视为最终版本，可投入回放模式使用。

## 脚本生命周期

```
探索 → 生成 → 固化 → 回放
  │                 │
  │  自动保存到     │  标记脚本为
  │  scripts/<step>.py  │  生产就绪
  │                 │
  └─────────────────┘
```

## 本地脚本文件

```
case_dir/
├── case.py
├── scripts/
│   ├── my_step.py           # 自动生成的回放脚本
│   ├── .my_step.solidified   # 固化标记文件
│   ├── another_step.py
│   └── .another_step.solidified
└── ...
```
