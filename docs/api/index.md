# API Reference

Skiritai's public API is designed to be minimal and intuitive. Here's an overview of the key modules.

## Core Modules

| Module                              | Description                                                    |
|-------------------------------------|----------------------------------------------------------------|
| [BaseCase](/api/base-case)          | Base class for test cases, with decorators and lifecycle       |
| [AIContext](/api/ai-context)        | Explore/replay execution context passed to each step           |
| [Tools](/api/tools)                 | 16 Playwright + DOM perception tools available to the AI agent |
| [LLM Providers](/api/llm-providers) | Pluggable LLM backend abstraction                              |
| [Event Bus](/api/event-bus)         | Async pub-sub event system                                     |

## Package Entry Point

```python
from skiritai import (
    BaseCase,
    step,
    step_mode,
    on_failure,
    run_case,
    AIContext,
)
```

For detailed API docs, check each module page.
