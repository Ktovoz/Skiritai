# BaseCase

`BaseCase` 是所有测试用例的基类，位于 `skiritai.core.base_case`。

## 构造函数

```python
BaseCase(
    case_dir: Path | None = None,   # 默认：文件所在目录
    execution_id: str | None = None, # 默认："default"
    results_dir: Path | None = None, # 保存截图/结果的目录
)
```

## 装饰器

### `@step`

将 async 方法标记为测试步骤。方法接收 `self` 和 `ai: AIContext`：

```python
@step
async def my_action(self, ai):
    await ai.action("导航到登录页面并输入凭证")
```

不加 `@step` 但第二个参数为 `ai` 的方法仍然可用（向后兼容），但推荐使用 `@step`。

### `@step_mode(mode)`

控制步骤的执行模式：

| 模式 | 行为 |
|------|----------|
| `"auto"` | 有脚本且成功则回放；失败时回退到探索（默认） |
| `"explore"` | 始终使用 AI Agent，覆盖已有回放脚本 |
| `"replay"` | 始终使用回放脚本；无脚本时报错 |

### `@on_failure(policy, max_retries=1)`

设置步骤失败处理策略：

| 策略 | 行为 |
|--------|----------|
| `FailurePolicy.ABORT` | 立即停止所有执行（默认） |
| `FailurePolicy.SKIP` | 跳过此步骤，继续执行下一个 |
| `FailurePolicy.RETRY` | 最多重试 `max_retries` 次后终止 |

```python
from skiritai import on_failure, FailurePolicy

class MyTest(BaseCase):
    @on_failure(FailurePolicy.RETRY, max_retries=3)
    @step
    async def retry_flaky(self, ai):
        await ai.action("点击偶尔延迟出现的按钮")
```

## 生命周期

1. `setup()` — 在所有步骤之前调用（默认：启动浏览器）
2. `before_step(step_name)` — 每个步骤前调用的钩子
3. 每个 `@step` 方法按定义顺序执行
4. `after_step(step_name, result)` — 每个步骤后调用的钩子（成功或失败均调用）
5. `on_step_error(step_name, error)` — 步骤抛出异常时调用的钩子；返回 `StepResult` 控制流程
6. `teardown()` — 在所有步骤之后调用（始终执行；默认：关闭浏览器）
7. 设置 `results_dir` 后，失败时自动截图

## 浏览器生命周期方法

```python
await self.launch_browser()            # 标准模式（进程内）
await self.launch_browser_persistent() # 持久化模式（独立 CDP 子进程）
await self.disconnect_browser()        # 断开连接，不关闭浏览器
await self.reconnect_browser()         # 重新连接到持久化会话
await self.terminate_browser()         # 终止持久化浏览器 + 清理
await self.close_browser()             # 关闭标准浏览器
```

详见[浏览器会话](/zh/guide/browser-sessions)。
