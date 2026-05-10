# 事件总线

事件总线（`skiritai.events`）提供执行引擎与外部观察者（如 WebSocket 服务器）之间的异步发布-订阅消息传递。

## 特性

- **内存历史缓冲区** — 每次执行的事件历史记录（默认最多 500 条）
- **JSONL 文件持久化** — 可选，用于运行后分析和回放
- **异步发布** — 非阻塞事件发射到所有匹配的订阅者
- **历史回放** — 延迟订阅者可通过 `get_history()` 回放过去的事件

## 用法

```python
from skiritai.events import EventBus, Event

bus = EventBus()

# 订阅特定事件类型
async def handle_step(event: Event):
    print(f"{event.type}: {event.data}")

bus.subscribe(handle_step, ["step_started", "step_completed"])

# 订阅所有事件
bus.subscribe(handle_step)

# 发布
await bus.publish(Event(
    type="step_started",
    execution_id="my_case",
    data={"step_id": "login"},
))

# 获取历史（重连后追回）
history = bus.get_history("my_case")

# 可选：将事件持久化到磁盘
bus.enable_persistence(Path("./event_logs"))

# 上下文管理器——退出时自动取消订阅
with bus.subscribed(handle_step, ["step_completed"]):
    ...  # handler 在此范围内有效
```

## 事件类型

| 事件                    | 描述                           |
|-----------------------|------------------------------|
| `step_started`        | 步骤开始执行                       |
| `step_completed`      | 步骤执行成功                       |
| `step_failed`         | 步骤执行失败，带有错误信息                |
| `tool_called`         | AI Agent 调用了 Playwright/感知工具 |
| `execution_started`   | 完整用例执行开始                     |
| `execution_completed` | 完整用例执行结束                     |
| `log_message`         | 执行引擎的日志消息                    |

## 模块级单例

```python
from skiritai.events import event_bus

# 可像任何 EventBus 实例一样使用
event_bus.subscribe(my_handler)
```
