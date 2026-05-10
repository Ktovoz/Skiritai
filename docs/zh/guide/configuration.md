# 配置

Skiritai 通过环境变量进行配置。

## LLM 设置

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | — |
| `OPENAI_BASE_URL` | OpenAI 兼容端点 | `https://api.openai.com/v1` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | — |
| `LLM_PROVIDER` | 明确指定 LLM 提供商（`openai` / `anthropic`） | 自动检测 |
| `LLM_MODEL` | 模型名称 | `gpt-4o` |
| `LLM_MAX_RETRIES` | LLM 调用最大重试次数 | `3` |
| `LLM_RETRY_BASE_DELAY` | 指数退避的基础延迟（秒） | `2.0` |
| `LLM_RETRY_MAX_DELAY` | 两次重试之间的最大延迟（秒） | `60.0` |

## 系统提示词

AI Agent 的系统提示词按以下优先级解析：

1. **用例级** — 用例目录下的 `prompt.md` 或 `prompt.txt`
2. **环境文件** — `SYSTEM_PROMPT_FILE` 指向的 Markdown 文件
3. **环境内联** — `SYSTEM_PROMPT` 环境变量
4. **内置默认** — Skiritai 附带的中文提示词

## 浏览器设置

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `SKIRITAI_HEADLESS` / `HEADLESS` | 无头模式运行浏览器 | `false` |
| `SKIRITAI_CHROME_PATH` / `CHROME_PATH` | 自定义 Chromium 可执行文件路径 | Playwright 内置 Chromium |
| `CI` | CI 环境检测（自动添加 `--no-sandbox`） | — |

## 日志

Skiritai 使用 [Loguru](https://github.com/Delgan/loguru)。

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `SKIRITAI_LOG_LEVEL` / `LOG_LEVEL` | 日志级别 | `INFO` |
| `SKIRITAI_LOG_DIR` | 日志文件目录 | `.skiritai/logs` |

```bash
SKIRITAI_LOG_LEVEL=DEBUG skiritai run .
```

## Web 服务器

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `SKIRITAI_CASES_ROOT` | Web 模式下用例发现的根目录 | `./examples` |
| `SKIRITAI_CORS_ORIGINS` / `CORS_ALLOWED_ORIGINS` | CORS 允许的来源 | — |

## 用例文件

| 文件 | 用途 |
|------|------|
| `<case_dir>/prompt.md` 或 `prompt.txt` | 用例级自定义系统提示词（最高优先级） |
| `<case_dir>/scripts/<step>.py` | 自动生成的回放脚本 |
| `<case_dir>/scripts/.<step>.solidified` | 脚本固化标记文件 |
| `<case_dir>/.browser_session` | 持久化浏览器会话信息（CDP 端口 + PID） |
| `<case_dir>/.case_context` | 用例执行上下文快照 |
