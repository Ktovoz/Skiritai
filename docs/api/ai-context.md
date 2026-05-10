# AIContext

`AIContext` is the object passed as the `ai` parameter to every `@step` method. It manages the explore/replay lifecycle.

## Core Method

### `ai.action(description, mode=None)`

The primary interface to the browser. Takes a **natural language description** of what to do — the AI agent interprets
and executes it.

```python
@step
async def login(self, ai):
    await ai.action("Navigate to the login page and enter credentials")
    await ai.action("Click the submit button and verify login succeeds")
```

The AI agent uses built-in tools (navigate, click, fill, page_perceive, find_element, etc.) to figure out and execute
the right sequence of Playwright operations. After a successful exploration, it generates a replay script so subsequent
runs can skip the AI and execute at full speed.

**Parameters:**

- `description` — Natural language description of the task to perform
- `mode` — Optional execution mode override: `"auto"` (default), `"explore"`, or `"replay"`

**Returns:** `dict` with `success`, `summary`, and `steps` keys.

## Execution Modes

| Mode        | Behavior                                                                         |
|-------------|----------------------------------------------------------------------------------|
| `"auto"`    | Replay if script exists and succeeds; on failure, fall back to explore (default) |
| `"explore"` | Always run AI agent, overwrite any existing replay script                        |
| `"replay"`  | Always run replay script; error if no script exists                              |

Set the default mode per-step with `@step_mode`, or override per-call:

```python
@step_mode("explore")
@step
async def unstable_page(self, ai):
    # Always explore, never replay
    await ai.action("Navigate to the dynamic dashboard")

@step
async def mixed_mode(self, ai):
    # First action uses default (auto), second forces explore
    await ai.action("Check the homepage")
    await ai.action("Re-analyze the updated chart", mode="explore")
```

## Replay Scripts

After `ai.action()` succeeds in explore mode, a replay script is auto-generated at `<case_dir>/scripts/<step_name>.py`.
The script can be:

- Run independently: `python scripts/my_step.py`
- Imported: `await run(page, context)`
- Edited via the Web API
- Solidified to lock a version for replay mode (via `POST /scripts/{step}/solidify`)

See [Replay Scripts](/guide/replay-scripts) for details.
