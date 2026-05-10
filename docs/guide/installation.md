# Installation

## Prerequisites

- **Python** 3.11 or later
- **Node.js** 18+ (for Playwright browsers)

## Install Skiritai

### From PyPI (recommended)

```bash
pip install skiritai
```

### With optional dependencies

```bash
# Web server
pip install skiritai[web]

# Anthropic Claude support
pip install skiritai[anthropic]

# Everything
pip install skiritai[web,anthropic]
```

### From source

```bash
git clone https://github.com/Ktovoz/Skiritai.git
cd Skiritai
pip install -e .
```

## Install Playwright browsers

```bash
playwright install chromium
```

## Configure your LLM

Create a `.env` file in your project root:

```bash
# OpenAI / OpenAI-compatible
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Or for Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
```

## Verify

```bash
skiritai list examples/
```

You should see the sample test cases listed.
