# Writing Test Cases

Test cases are Python classes that inherit from `BaseCase`. Each step is an `async` method decorated with `@step`.

## Basic Structure

```python
from skiritai import BaseCase, step, run_case

class MyTestCase(BaseCase):
    @step
    async def step_one(self, ai):
        # ai is an AIContext instance — your interface to the browser
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

## Step Execution Modes

Control how AI explores each step with `@step_mode`:

```python
from skiritai import step_mode

class MyTest(BaseCase):
    @step_mode("explore")  # Always use AI, overwrite existing script
    @step
    async def always_explore(self, ai):
        await ai.navigate("https://example.com")

    @step_mode("replay")   # Only use replay script, error if missing
    @step
    async def replay_only(self, ai):
        await ai.click("#button")

    @step_mode("auto")     # Default: replay if script exists, else explore
    @step
    async def smart(self, ai):
        await ai.fill("#input", "text")
```

## Failure Handling

```python
from skiritai import on_failure

class MyTest(BaseCase):
    @on_failure("SKIP")  # SKIP, ABORT, or RETRY
    @step
    async def optional_step(self, ai):
        await ai.click("#might-not-exist")
```

## Case-Level Configuration

```python
class MyTest(BaseCase):
    timeout = 60          # seconds
    case_dir = __file__   # directory for scripts/screenshots
    results_dir = "./results"
```
