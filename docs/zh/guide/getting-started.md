# 快速开始

Skiritai 是一个 AI 驱动的浏览器测试自动化框架。它使用 LLM 探索 Web 应用，并生成可回放的 Playwright 脚本。

## 工作原理

Skiritai 采用两阶段循环：

1. **探索（Explore）** — AI Agent 分析页面，决定要执行的操作，并通过 Playwright 执行，同时记录每一步。
2. **回放（Replay）** — 记录的步骤被编译为独立的 Python 脚本。回放速度约快 30 倍，因为不再依赖 LLM。

```python
# example.py
from skiritai import BaseCase, step, run_case

class MyTest(BaseCase):
    """在 GitHub 上搜索 Skiritai。"""

    @step
    async def search_github(self, ai):
        await ai.navigate("https://github.com")
        await ai.fill("input[name='q']", "Skiritai AI testing")
        await ai.click("button[type='submit']")

    @step
    async def verify_results(self, ai):
        text = await ai.get_text("main")
        assert "Skiritai" in text

if __name__ == "__main__":
    run_case(MyTest)
```

运行：

```bash
skiritai run . --case example.py
```

第一次运行时，AI 会探索并找出正确的选择器。后续运行时，生成的回放脚本直接全速执行。
