# LLM 提供商

Skiritai 使用可插拔的 LLM 提供商系统，定义在 `skiritai.llm` 中。

## 架构

```
skiritai.llm
├── base.py          # 抽象 LLMProvider 基类
├── registry.py      # 自动检测可用提供商
├── openai_provider.py    # OpenAI / OpenAI 兼容
└── anthropic_provider.py # Anthropic Claude
```

## 内置提供商

### OpenAI 提供商

适用于任何兼容 OpenAI API 的服务（GPT、通义千问 via SiliconFlow、GPTsAPI 等）：

```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### Anthropic 提供商

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

需要 `pip install skiritai[anthropic]`。

## 添加自定义提供商

1. 继承 `skiritai.llm.base` 中的 `LLMProvider`
2. 实现抽象方法
3. 注册表会根据环境变量自动检测可用提供商
