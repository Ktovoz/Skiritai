# API 参考

Skiritai 的公共 API 设计简洁直观。以下是核心模块概览。

## 核心模块

| 模块 | 描述 |
|--------|-------------|
| [BaseCase](/zh/api/base-case) | 测试用例基类，含装饰器与生命周期 |
| [AIContext](/zh/api/ai-context) | 每个步骤中使用的探索/回放执行上下文 |
| [工具](/zh/api/tools) | 供 AI Agent 使用的 16 个 Playwright + DOM 感知工具 |
| [LLM 提供商](/zh/api/llm-providers) | 可插拔的 LLM 后端抽象 |
| [事件总线](/zh/api/event-bus) | 异步发布-订阅事件系统 |

## 包入口

```python
from skiritai import (
    BaseCase,
    step,
    step_mode,
    on_failure,
    run_case,
    AIContext,
)
```

详细 API 文档请查看各模块页面。
