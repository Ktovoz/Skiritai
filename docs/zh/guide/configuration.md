# 配置

Skiritai 通过环境变量进行配置。

## LLM 设置

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | — |
| `OPENAI_BASE_URL` | OpenAI 兼容端点 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | — |

## 系统提示词

AI Agent 的系统提示词按以下优先级解析：

1. **用例级** — 用例目录下的 `prompt.md`
2. **环境文件** — `SYSTEM_PROMPT_FILE` 指向的 Markdown 文件
3. **环境内联** — `SYSTEM_PROMPT` 环境变量
4. **内置默认** — Skiritai 附带的中文提示词

## 浏览器设置

| 变量 | 描述 | 默认值 |
|----------|-------------|---------|
| `HEADLESS` | 无头模式运行浏览器 | `false` |
| `BROWSER_TIMEOUT` | 浏览器操作超时（毫秒） | `30000` |

## 日志

Skiritai 使用 [Loguru](https://github.com/Delgan/loguru)。设置日志级别：

```bash
LOGURU_LEVEL=DEBUG skiritai run .
```
