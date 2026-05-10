# Event Bus

The Event Bus (`skiritai.events`) provides async publish-subscribe messaging between the execution engine and external observers (like the WebSocket server).

## Features

- **In-memory history buffer** — per-execution event history (default max 500 events)
- **JSONL file persistence** — optional, for post-run analysis and replay
- **Async publishing** — non-blocking event emission to all matching subscribers
- **History catch-up** — late subscribers can replay past events via `get_history()`

## Usage

```python
from skiritai.events import EventBus, Event

bus = EventBus()

# Subscribe to specific event types
async def handle_step(event: Event):
    print(f"{event.type}: {event.data}")

bus.subscribe(handle_step, ["step_started", "step_completed"])

# Subscribe to all events
bus.subscribe(handle_step)

# Publish
await bus.publish(Event(
    type="step_started",
    execution_id="my_case",
    data={"step_id": "login"},
))

# Get history (for catch-up after reconnection)
history = bus.get_history("my_case")

# Optional: persist events to disk
bus.enable_persistence(Path("./event_logs"))

# Context manager — auto-unsubscribes on exit
with bus.subscribed(handle_step, ["step_completed"]):
    ...  # handler is active
```

## Event Types

| Event | Description |
|-------|-------------|
| `step_started` | A step began execution |
| `step_completed` | A step completed successfully |
| `step_failed` | A step failed with an error |
| `tool_called` | The AI agent called a Playwright/perception tool |
| `execution_started` | The full test case execution began |
| `execution_completed` | The full test case execution finished |
| `log_message` | A log message from the execution engine |

## Module-Level Singleton

```python
from skiritai.events import event_bus

# Use like any EventBus instance
event_bus.subscribe(my_handler)
```
