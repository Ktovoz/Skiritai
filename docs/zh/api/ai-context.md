# AIContext

`AIContext` 是每个 `@step` 方法中作为 `ai` 参数传入的对象。它管理探索/回放生命周期。

## 核心方法

### `ai.action(description, mode=None)`

与浏览器交互的主要接口。接收**自然语言描述**，AI Agent 负责解释和执行。

```python
@step
async def login(self, ai):
    await ai.action("导航到登录页面并输入凭证")
    await ai.action("点击提交按钮并验证登录成功")
```

AI Agent 使用内置工具（navigate、click、fill、page_perceive、find_element 等）来推断并执行正确的 Playwright
操作序列。探索成功后，自动生成回放脚本，后续运行可跳过 AI 直接全速执行。

**参数：**

- `description` — 要执行的任务的自然语言描述
- `mode` — 可选的执行模式覆盖：`"auto"`（默认）、`"explore"` 或 `"replay"`

**返回：** 包含 `success`、`summary` 和 `steps` 的字典。

## 执行模式

| 模式          | 行为                     |
|-------------|------------------------|
| `"auto"`    | 有脚本且成功则回放；失败时回退到探索（默认） |
| `"explore"` | 始终运行 AI Agent，覆盖已有回放脚本 |
| `"replay"`  | 始终运行回放脚本；无脚本时报错        |

通过 `@step_mode` 为每个步骤设置默认模式，或逐个调用覆盖：

```python
@step_mode("explore")
@step
async def unstable_page(self, ai):
    # 始终探索，绝不回放
    await ai.action("导航到动态仪表盘")

@step
async def mixed_mode(self, ai):
    # 第一个操作用默认（auto），第二个强制探索
    await ai.action("检查首页")
    await ai.action("重新分析更新后的图表", mode="explore")
```

## 回放脚本

`ai.action()` 在探索模式下成功后，自动在 `<case_dir>/scripts/<step_name>.py` 生成回放脚本。脚本可以：

- 独立运行：`python scripts/my_step.py`
- 导入使用：`await run(page, context)`
- 通过 Web API 编辑
- 固化以锁定回放版本（通过 `POST /scripts/{step}/solidify`）

详见[回放脚本](/zh/guide/replay-scripts)。
