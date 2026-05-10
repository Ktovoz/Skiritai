# 编写测试用例

测试用例是继承 `BaseCase` 的 Python 类。每个步骤是用 `@step` 装饰的 `async` 方法。

## 基本结构

```python
from skiritai import BaseCase, step, run_case

class MyTestCase(BaseCase):
    @step
    async def step_one(self, ai):
        # ai 是 AIContext 实例——你与浏览器交互的接口
        await ai.navigate("https://example.com")
        await ai.click("#my-button")
        text = await ai.get_text(".result")
        assert "expected" in text

    @step
    async def step_two(self, ai):
        await ai.fill("#input", "hello")
        await ai.click("#submit")

if __name__ == "__main__":
    run_case(MyTestCase)
```

## 步骤执行模式

使用 `@step_mode` 控制 AI 探索行为：

```python
from skiritai import step_mode

class MyTest(BaseCase):
    @step_mode("explore")  # 始终使用 AI，覆盖已有脚本
    @step
    async def always_explore(self, ai):
        await ai.navigate("https://example.com")

    @step_mode("replay")   # 仅使用回放脚本，缺失则报错
    @step
    async def replay_only(self, ai):
        await ai.click("#button")

    @step_mode("auto")     # 默认：有脚本则回放，否则探索
    @step
    async def smart(self, ai):
        await ai.fill("#input", "text")
```

## 失败处理

```python
from skiritai import on_failure

class MyTest(BaseCase):
    @on_failure("SKIP")  # SKIP、ABORT 或 RETRY
    @step
    async def optional_step(self, ai):
        await ai.click("#might-not-exist")
```

## 用例级配置

```python
class MyTest(BaseCase):
    timeout = 60          # 秒
    case_dir = __file__   # 脚本/截图存放目录
    results_dir = "./results"
```
