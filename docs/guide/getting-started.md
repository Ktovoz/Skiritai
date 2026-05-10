# Getting Started

Skiritai is an AI-driven browser test automation framework. It uses LLMs to explore web applications and generate replayable Playwright scripts.

## How It Works

Skiritai operates in a two-phase loop:

1. **Explore** — An AI agent analyzes the page, decides what actions to take, and executes them via Playwright. It records every step.
2. **Replay** — The recorded steps are compiled into a standalone Python script. Replaying it is ~30x faster because no LLM is involved.

```python
# example.py
from skiritai import BaseCase, step, run_case

class MyTest(BaseCase):
    """Search for Skiritai on GitHub."""

    @step
    async def search_github(self, ai):
        await ai.navigate("https://github.com")
        await ai.fill("input[name='q']", "Skiritai AI testing")
        await ai.click("button[type='submit']")

    @step
    async def verify_results(self, ai):
        text = await ai.get_text("main")
        assert "Skiritai" in text

if __name__ == "__main__":
    run_case(MyTest)
```

Run it:

```bash
skiritai run . --case example.py
```

On the first run, the AI explores and figures out the right selectors. On subsequent runs, the generated replay script runs directly at full speed.
