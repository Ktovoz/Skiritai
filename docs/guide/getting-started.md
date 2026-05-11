# Getting Started

Skiritai is an AI-driven browser test automation framework. It uses LLMs to explore web applications and generate
replayable Playwright scripts.

## How It Works

Skiritai operates in a two-phase loop:

1. **Explore** — An AI agent analyzes the page, decides what actions to take, and executes them via Playwright. It
   records every step.
2. **Replay** — The recorded steps are compiled into a standalone Python script. Replaying it is ~30x faster because no
   LLM is involved.

```python
# example.py
from skiritai import BaseCase, step, run_case

class MyTest(BaseCase):
    """Search for Skiritai on GitHub."""

    @step
    async def search_github(self, ai):
        await ai.action("导航到 GitHub 并搜索 Skiritai AI testing")

    @step
    async def verify_results(self, ai):
        await ai.action("验证搜索结果包含 Skiritai")

if __name__ == "__main__":
    run_case(MyTest)
```

Run it:

```bash
skiritai run . --case example.py
```

On the first run, the AI explores and figures out the right selectors. On subsequent runs, the generated replay script
runs directly at full speed.

## Alternative: Flow API (No Subclass)

Prefer a functional style? Use the [Flow API](/guide/flow-api) — no `BaseCase`, no decorators:

```python
from skiritai import flow

async with flow() as ai:
    await ai.action("Navigate to GitHub and search for Skiritai")
    await ai.verify("Search results include Skiritai")
```

## Alternative: YAML Cases (No Code)

No Python at all? Define your test in [YAML](/guide/yaml-cases):

```yaml
# case.yaml
steps:
  - action: Navigate to GitHub and search for Skiritai
  - verify: Search results include Skiritai
```

```bash
skiritai run .
```
