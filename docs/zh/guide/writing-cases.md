# 编写测试用例

测试用例是继承 `BaseCase` 的 Python 类。每个步骤是用 `@step` 装饰的 `async` 方法。

::: tip 其他编写方式
- **[Flow API](/zh/guide/flow-api)** — 函数式风格，`async with flow() as ai:`，无需继承。
- **[YAML 用例](/zh/guide/yaml-cases)** — 用 YAML 定义测试步骤，无需编写 Python 代码。
:::

## 基本结构

```python
from skiritai import BaseCase, step, run_case

class MyTestCase(BaseCase):
    @step
    async def step_one(self, ai):
        # ai 是 AIContext 实例——你与浏览器交互的接口
        # ai.action() 接收自然语言描述
        ai.action('点击 #my-button，然后验证结果区域包含 "expected"')

    @step
    async def step_two(self, ai):
        ai.action('在 #input 输入 "hello"，然后点击 #submit')

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
        await ai.action("导航到 example.com")

    @step_mode("replay")   # 仅使用回放脚本，缺失则报错
    @step
    async def replay_only(self, ai):
        await ai.action("点击 #button")

    @step_mode("auto")     # 默认：有脚本则回放，否则探索
    @step
    async def smart(self, ai):
        await ai.action("在 #input 输入 'text'")
```

## 失败处理

```python
from skiritai import on_failure, FailurePolicy

class MyTest(BaseCase):
    @on_failure(FailurePolicy.SKIP)  # 跳过失败步骤，继续执行
    @step
    async def optional_step(self, ai):
        await ai.action("点击 #might-not-exist")

    @on_failure(FailurePolicy.RETRY, max_retries=2)  # 最多重试 2 次
    @step
    async def flaky_step(self, ai):
        await ai.action("点击偶尔延迟出现的按钮")

    @on_failure(FailurePolicy.ABORT)  # 立即停止（默认）
    @step
    async def critical_step(self, ai):
        await ai.action("执行关键操作")
```

## 用例级配置

`case_dir`、`execution_id`、`results_dir` 通过构造函数传入。更多配置通过环境变量设置（参见[配置](/zh/guide/configuration)）。
