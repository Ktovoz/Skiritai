# Event Bus

The Event Bus (`skiritai.events`) provides async pub-sub messaging between the execution engine and external observers (like the WebSocket server).

## Features

- **In-memory history buffer** — per-execution event history
- **JSONL file persistence** — optional, for post-run analysis
- **Async publishing** — non-blocking event emission

## Usage

```python
from skiritai.events import EventBus

bus = EventBus()

# Subscribe
async def handle_event(event):
    print(f"{event.type}: {event.data}")

bus.subscribe("step_start", handle_event)

# Publish
await bus.publish("step_start", {"step": "login"})
```

## Event Types

| Event | Description |
|-------|-------------|
| `step_start` | A step began execution |
| `step_end` | A step completed |
| `tool_call` | The AI agent called a tool |
| `tool_result` | A tool returned a result |
| `screenshot` | A screenshot was captured |
| `error` | An error occurred |
