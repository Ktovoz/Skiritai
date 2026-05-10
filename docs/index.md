---
layout: home

hero:
  name: "Skiritai"
  text: "AI-Driven Browser Test Automation"
  tagline: Named after Sparta's elite reconnaissance troops — explore first, then execute at 30x speed.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/Ktovoz/Skiritai
  image:
    src: /logo.svg
    alt: Skiritai

features:
  - icon: 🧠
    title: AI-Powered Exploration
    details: Uses LLM-based ReAct agent to analyze pages, discover UI elements, and determine the correct sequence of actions — no brittle selectors.
  - icon: ⚡
    title: 30x Replay Speed
    details: Once explored, the agent generates standalone Python scripts that execute directly against Playwright with zero AI overhead.
  - icon: 🔤
    title: CJK-Aware Element Matching
    details: Specialized scoring for Chinese, Japanese, and Korean text makes element discovery more accurate in non-English UIs.
  - icon: 🔧
    title: Persistent Browser Sessions
    details: Optional CDP-based browser lifecycle that survives Python restarts, so you can resume exploration without losing state.
  - icon: 🌐
    title: Web Dashboard (Optional)
    details: FastAPI server with REST + WebSocket APIs for triggering, monitoring, and controlling test runs remotely.
  - icon: 📦
    title: Multi-LLM Support
    details: Works with OpenAI-compatible APIs (GPT, Qwen), Anthropic Claude, and more via a pluggable provider system.
---
