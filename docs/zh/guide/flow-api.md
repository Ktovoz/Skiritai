# Flow API

Flow API 是一种函数式、无需继承的测试编写方式。无需继承 `BaseCase`，只需使用 `async with` 上下文管理器。

## 基本用法

```python
import asyncio
from skiritai import flow

async def main():
    async with flow() as ai:
        await ai.action("导航到 https://www.baidu.com")
        await ai.screenshot("homepage")
        result = await ai.verify("页面标题包含'百度'")
        print(f"验证: {'通过' if result['passed'] else '失败'}")

asyncio.run(main())
```

`flow()` 启动浏览器，提供 `ai` 对象，并在代码块退出时自动关闭浏览器。

## 可用方法

| 方法 | 说明 |
|---|---|
| `ai.action(description, mode=None)` | 通过 AI 智能体执行自然语言操作 |
| `ai.verify(assertion, take_screenshot=True)` | 执行 AI 驱动的断言（失败时不阻断执行） |
| `ai.screenshot(name)` | 截取全页截图 |
| `ai.analyze_page()` | 分析页面 DOM（缓存结果，自动注入后续的 `action()` 调用） |
| `ai.get_page_info()` | 获取页面标题、URL 和文本摘要（缓存） |

## 配置

```python
from pathlib import Path

async with flow(
    headless=True,                   # 无头模式运行浏览器
    results_dir=Path("results"),     # 报告和截图保存目录
    max_steps=20,                    # 每个 action 的最大工具调用步数
) as ai:
    await ai.action("...")
```

所有参数均为可选。`headless` 默认读取 `HEADLESS` 环境变量。

## 与 BaseCase 的区别

| 特性 | BaseCase | Flow API |
|---|---|---|
| 结构 | 类 + 装饰器（`@step`、`@step_mode`） | 扁平的 `async with` 代码块 |
| 浏览器生命周期 | 手动管理 `setup/teardown` | 自动管理 |
| 步骤跟踪 | 由方法名自动生成 | 自动生成步骤 ID |
| 适用场景 | 结构化测试套件、可复用用例 | 快速脚本、一次性探索 |
| 回放脚本 | `scripts/` 目录下的逐步骤 `.py` 文件 | 相同的探索→回放循环 |
