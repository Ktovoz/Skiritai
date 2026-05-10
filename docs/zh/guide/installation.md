# 安装

## 环境要求

- **Python** 3.11 或更高版本
- **Node.js** 18+ （Playwright 浏览器所需）

## 安装 Skiritai

### 从源码安装（当前推荐方式）

```bash
git clone https://github.com/Ktovoz/Skiritai.git
cd Skiritai
pip install -e .
```

### 安装可选依赖

```bash
# Web 服务器
pip install -e ".[web]"

# Anthropic Claude 支持
pip install -e ".[anthropic]"

# 全部安装
pip install -e ".[web,anthropic]"
```

## 安装 Playwright 浏览器

```bash
playwright install chromium
```

## 配置 LLM

在项目根目录创建 `.env` 文件：

```bash
# OpenAI / OpenAI 兼容
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 或使用 Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
```

## 验证安装

```bash
skiritai list examples/
```

你应该能看到列出的示例测试用例。
