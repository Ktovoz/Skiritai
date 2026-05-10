# LLM Providers

Skiritai uses a pluggable LLM provider system defined in `skiritai.llm`.

## Architecture

```
skiritai.llm
├── base.py          # Abstract LLMProvider base class
├── registry.py      # Auto-detection of available providers
├── openai_provider.py    # OpenAI / OpenAI-compatible
└── anthropic_provider.py # Anthropic Claude
```

## Built-in Providers

### OpenAI Provider

Works with any OpenAI-compatible API (GPT, Qwen via SiliconFlow, GPTsAPI, etc.):

```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### Anthropic Provider

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Requires `pip install skiritai[anthropic]`.

## Adding a Custom Provider

1. Subclass `LLMProvider` from `skiritai.llm.base`
2. Implement the abstract methods
3. The registry auto-detects available providers from environment variables
