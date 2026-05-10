# Configuration

Skiritai can be configured via environment variables.

## LLM Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Model name | `gpt-4o` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |

## System Prompt

The AI agent's system prompt is resolved in this order:

1. **Case-level** — `prompt.md` in the case directory
2. **Env file** — `SYSTEM_PROMPT_FILE` pointing to a markdown file
3. **Env inline** — `SYSTEM_PROMPT` environment variable
4. **Built-in default** — Chinese-language prompt shipped with Skiritai

## Browser Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `HEADLESS` | Run browser headless | `false` |
| `BROWSER_TIMEOUT` | Browser action timeout (ms) | `30000` |

## Logging

Skiritai uses [Loguru](https://github.com/Delgan/loguru). Set the log level:

```bash
LOGURU_LEVEL=DEBUG skiritai run .
```
