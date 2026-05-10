# BaseCase

`BaseCase` is the base class all test cases inherit from. It lives in `skiritai.core.base_case`.

## Constructor

```python
BaseCase(
    case_dir: Path | None = None,   # default: file's parent directory
    execution_id: str | None = None, # default: "default"
    results_dir: Path | None = None, # for saving screenshots/results
)
```

## Decorators

### `@step`

Marks an async method as a test step. The method receives `self` and `ai: AIContext`:

```python
@step
async def my_action(self, ai):
    await ai.action("navigate to the login page and enter credentials")
```

Methods without `@step` that have `ai` as their second parameter still work for backward compatibility, but `@step` is recommended.

### `@step_mode(mode)`

Controls execution mode for a step:

| Mode | Behavior |
|------|----------|
| `"auto"` | Replay if script exists and succeeds; fall back to explore on failure (default) |
| `"explore"` | Always use AI agent, overwrite existing replay script |
| `"replay"` | Always use replay script; error if no script exists |

### `@on_failure(policy, max_retries=1)`

Sets failure handling for a step:

| Policy | Behavior |
|--------|----------|
| `FailurePolicy.ABORT` | Stop all execution immediately (default) |
| `FailurePolicy.SKIP` | Skip this step and continue to the next |
| `FailurePolicy.RETRY` | Retry the step up to `max_retries` times before aborting |

```python
from skiritai import on_failure, FailurePolicy

class MyTest(BaseCase):
    @on_failure(FailurePolicy.RETRY, max_retries=3)
    @step
    async def retry_flaky(self, ai):
        await ai.action("click the button that sometimes lags")
```

## Lifecycle

1. `setup()` — Called before all steps (default: launches browser)
2. `before_step(step_name)` — Hook called before each step
3. Each `@step` method runs in definition order
4. `after_step(step_name, result)` — Hook called after each step (success or failure)
5. `on_step_error(step_name, error)` — Hook called when a step raises; returns a `StepResult` to control flow
6. `teardown()` — Called after all steps (always runs; default: closes browser)
7. Screenshots are auto-captured on failure when `results_dir` is set

## Browser Lifecycle Methods

```python
await self.launch_browser()            # Standard mode (in-process)
await self.launch_browser_persistent() # Persistent mode (separate CDP process)
await self.disconnect_browser()        # Detach without killing browser
await self.reconnect_browser()         # Reattach to persistent session
await self.terminate_browser()         # Kill persistent browser + cleanup
await self.close_browser()             # Close standard browser
```

See [Browser Sessions](/guide/browser-sessions) for details on persistent mode.
