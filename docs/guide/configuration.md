# Configuration

Skiritai can be configured via environment variables.

## LLM Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `LLM_PROVIDER` | Explicit provider selection (`openai` / `anthropic`) | Auto-detect |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `LLM_MAX_RETRIES` | Max LLM call retries | `3` |
| `LLM_RETRY_BASE_DELAY` | Base delay for exponential backoff (seconds) | `2.0` |
| `LLM_RETRY_MAX_DELAY` | Max delay between retries (seconds) | `60.0` |

## System Prompt

The AI agent's system prompt is resolved in this order:

1. **Case-level** — `prompt.md` or `prompt.txt` in the case directory
2. **Env file** — `SYSTEM_PROMPT_FILE` pointing to a markdown file
3. **Env inline** — `SYSTEM_PROMPT` environment variable
4. **Built-in default** — Chinese-language prompt shipped with Skiritai

## Browser Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SKIRITAI_HEADLESS` / `HEADLESS` | Run browser headless | `false` |
| `SKIRITAI_CHROME_PATH` / `CHROME_PATH` | Custom Chromium executable path | Playwright's bundled Chromium |
| `CI` | CI detection (adds `--no-sandbox` automatically) | — |

## Logging

Skiritai uses [Loguru](https://github.com/Delgan/loguru).

| Variable | Description | Default |
|----------|-------------|---------|
| `SKIRITAI_LOG_LEVEL` / `LOG_LEVEL` | Log level | `INFO` |
| `SKIRITAI_LOG_DIR` | Log file directory | `.skiritai/logs` |

```bash
SKIRITAI_LOG_LEVEL=DEBUG skiritai run .
```

## Web Server

| Variable | Description | Default |
|----------|-------------|---------|
| `SKIRITAI_CASES_ROOT` | Root directory for case discovery in web mode | `./examples` |
| `SKIRITAI_CORS_ORIGINS` / `CORS_ALLOWED_ORIGINS` | CORS allowed origins | — |

## Per-Case Files

| File | Purpose |
|------|---------|
| `<case_dir>/prompt.md` or `prompt.txt` | Case-level custom system prompt (highest priority) |
| `<case_dir>/scripts/<step>.py` | Auto-generated replay script |
| `<case_dir>/scripts/.<step>.solidified` | Script solidification marker |
| `<case_dir>/.browser_session` | Persisted browser session info (CDP port + PID) |
| `<case_dir>/.case_context` | Case execution context snapshot |
