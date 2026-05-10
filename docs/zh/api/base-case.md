# BaseCase

`BaseCase` 是所有测试用例的基类，位于 `skiritai.core.base_case`。

## 类定义

```python
class BaseCase:
    timeout: int = 60
    case_dir: str | None = None
    results_dir: str = "./results"
```

## 装饰器

### `@step`

将 async 方法标记为测试步骤：

```python
@step
async def my_action(self, ai: AIContext):
    await ai.navigate("https://example.com")
```

### `@step_mode(mode)`

控制步骤的执行模式：

| 模式 | 行为 |
|------|----------|
| `"auto"` | 有回放脚本则回放，否则探索（默认） |
| `"explore"` | 始终使用 AI Agent |
| `"replay"` | 始终使用回放脚本 |

### `@on_failure(policy)`

设置步骤失败处理策略：

| 策略 | 行为 |
|--------|----------|
| `"ABORT"` | 停止所有执行（默认） |
| `"SKIP"` | 跳过此步骤，继续执行 |
| `"RETRY"` | 重试一次 |

## 生命周期

1. `setup()` — 在所有步骤之前调用
2. `teardown()` — 在所有步骤之后调用（始终执行）
3. 每个 `@step` 方法按定义顺序执行
4. 失败时自动截图
