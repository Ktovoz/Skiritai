# Writing Test Cases

Test cases are Python classes that inherit from `BaseCase`. Each step is an `async` method decorated with `@step`.

## Basic Structure

```python
from skiritai import BaseCase, step, run_case

class MyTestCase(BaseCase):
    @step
    async def step_one(self, ai):
        # ai is an AIContext instance — your interface to the browser
        # ai.action() takes a natural language description of what to do
        ai.action('点击 #my-button，然后验证结果区域包含 "expected"')

    @step
    async def step_two(self, ai):
        ai.action('在 #input 输入 "hello"，然后点击 #submit')

if __name__ == "__main__":
    run_case(MyTestCase)
```

## Step Execution Modes

Control how AI explores each step with `@step_mode`:

```python
from skiritai import step_mode

class MyTest(BaseCase):
    @step_mode("explore")  # Always use AI, overwrite existing script
    @step
    async def always_explore(self, ai):
        await ai.action("导航到 example.com")

    @step_mode("replay")   # Only use replay script, error if missing
    @step
    async def replay_only(self, ai):
        await ai.action("点击 #button")

    @step_mode("auto")     # Default: replay if script exists, else explore
    @step
    async def smart(self, ai):
        await ai.action("在 #input 输入 'text'")
```

## Failure Handling

```python
from skiritai import on_failure, FailurePolicy

class MyTest(BaseCase):
    @on_failure(FailurePolicy.SKIP)  # skip failed step and continue
    @step
    async def optional_step(self, ai):
        await ai.action("点击 #might-not-exist")

    @on_failure(FailurePolicy.RETRY, max_retries=2)  # retry up to 2 times
    @step
    async def flaky_step(self, ai):
        await ai.action("点击偶尔延迟出现的按钮")

    @on_failure(FailurePolicy.ABORT)  # stop immediately (default)
    @step
    async def critical_step(self, ai):
        await ai.action("执行关键操作")
```

## Case-Level Configuration

Class attributes such as `case_dir`、`execution_id`、`results_dir` are passed via the constructor. Additional
configuration comes from environment variables (see [Configuration](/guide/configuration)).
