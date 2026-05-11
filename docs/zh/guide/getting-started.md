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
        await ai.action("导航到 GitHub 并搜索 Skiritai AI testing")

    @step
    async def verify_results(self, ai):
        await ai.action("验证搜索结果包含 Skiritai")

if __name__ == "__main__":
    run_case(MyTest)
```

运行：

```bash
skiritai run . --case example.py
```

第一次运行时，AI 会探索并找出正确的选择器。后续运行时，生成的回放脚本直接全速执行。

## 另一种方式：Flow API（无需继承）

更喜欢函数式风格？试试 [Flow API](/zh/guide/flow-api) — 无需 `BaseCase`，无需装饰器：

```python
from skiritai import flow

async with flow() as ai:
    await ai.action("导航到 GitHub 并搜索 Skiritai")
    await ai.verify("搜索结果包含 Skiritai")
```

## 另一种方式：YAML 用例（零代码）

完全不想写 Python？用 [YAML](/zh/guide/yaml-cases) 定义测试：

```yaml
# case.yaml
steps:
  - action: 导航到 GitHub 并搜索 Skiritai
  - verify: 搜索结果包含 Skiritai
```

```bash
skiritai run .
```
