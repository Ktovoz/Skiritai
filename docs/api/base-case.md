# BaseCase

`BaseCase` is the base class all test cases inherit from. It lives in `skiritai.core.base_case`.

## Class Definition

```python
class BaseCase:
    timeout: int = 60
    case_dir: str | None = None
    results_dir: str = "./results"
```

## Decorators

### `@step`

Marks an async method as a test step:

```python
@step
async def my_action(self, ai: AIContext):
    await ai.navigate("https://example.com")
```

### `@step_mode(mode)`

Controls execution mode for a step:

| Mode | Behavior |
|------|----------|
| `"auto"` | Replay if script exists, else explore (default) |
| `"explore"` | Always use AI agent |
| `"replay"` | Always use replay script |

### `@on_failure(policy)`

Sets failure handling for a step:

| Policy | Behavior |
|--------|----------|
| `"ABORT"` | Stop all execution (default) |
| `"SKIP"` | Skip this step and continue |
| `"RETRY"` | Retry the step once |

## Lifecycle

1. `setup()` — Called before all steps
2. `teardown()` — Called after all steps (always runs)
3. Each `@step` method runs in order of definition
4. Screenshots are auto-captured on failure
