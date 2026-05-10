# Roadmap

Skiritai is evolving rapidly. Here's what's on the horizon.

## Visual Perception Layer

Current AI exploration relies on DOM analysis and CSS selectors. The next major evolution adds **visual perception** — the agent will "see" the page like a human tester.

### Visual-based AI Exploration

- **Screenshot understanding** — the agent interprets page screenshots to identify UI elements by their visual appearance, not just DOM structure
- **Canvas & WebGL support** — interact with interfaces that lack accessible DOM (charts, games, media players)
- **Layout-aware navigation** — understand spatial relationships between elements for more natural interaction patterns

### Multimodal Model Support

- **Vision-Language Models** — leverage GPT-4o, Claude 3.5 Sonnet, Gemini and other VLMs for richer page understanding
- **Native multimodal models** — support models with built-in vision capabilities, reducing the need for separate DOM analysis steps
- **Model-agnostic perception** — the perception layer adapts to whichever model is configured, automatically selecting the best strategy

### Visual Regression Detection

- **Cross-run screenshot comparison** — automatically detect unexpected UI changes between test executions
- **Diff highlights** — generate visual diffs showing exactly what changed on the page
- **Baseline management** — maintain approved screenshot baselines and flag deviations

---

## Multi-Platform Testing

Skiritai currently supports **Web** testing via Playwright/Chromium. We plan to extend the same Explore → Replay workflow to additional platforms.

### Current: Web

- Playwright-based browser automation
- 14 built-in tools (navigate, click, fill, scroll, etc.)
- Persistent browser sessions via CDP

### Planned: Mobile (iOS / Android)

- Appium or browser-use mobile integration
- Same `BaseCase` API — write test cases once, run on mobile devices
- Touch gesture support (tap, swipe, pinch)
- Real device and emulator/simulator support

### Planned: API Testing

- HTTP request tools for the AI agent (GET, POST, PUT, DELETE)
- JSON schema validation and response assertions
- Mix API calls with browser steps in a single test case
- Authentication flow support (OAuth, API keys, JWT)

### Under Investigation: Desktop

- Playwright Electron support for Electron apps
- OS-level automation for native desktop applications
- Cross-window interaction patterns

### The Vision

The goal is a **unified test framework** where the same Explore → Replay workflow works across Web, Mobile, and API — write once, test everywhere.

```python
class CrossPlatformCase(BaseCase):
    async def web_login(self):
        await self.ai.action("Login to the web app")

    async def api_check(self):
        await self.ai.action("Verify the user profile API returns correct data")

    async def mobile_notification(self):
        await self.ai.action("Check the push notification appears on mobile")
```

---

## Recently Completed

| Feature | Description |
|---------|-------------|
| **Visual Reports** | Vue 3 + Ant Design standalone HTML report with screenshots, assertions, and step details |
| **`ai.screenshot()`** | Capture named screenshots during test execution |
| **`ai.verify()`** | Assertion API for natural-language verification checks |
| **`@max_steps`** | Per-step agent recursion limit decorator |
| **Failure Policies** | `@on_failure(SKIP/RETRY)` for resilient multi-step flows |
