# 事件总线

事件总线（`skiritai.events`）提供执行引擎与外部观察者（如 WebSocket 服务器）之间的异步发布-订阅消息传递。

## 特性

- **内存历史缓冲区** — 每次执行的事件历史记录
- **JSONL 文件持久化** — 可选，用于运行后分析
- **异步发布** — 非阻塞事件发射

## 用法

```python
from skiritai.events import EventBus

bus = EventBus()

# 订阅
async def handle_event(event):
    print(f"{event.type}: {event.data}")

bus.subscribe("step_start", handle_event)

# 发布
await bus.publish("step_start", {"step": "login"})
```

## 事件类型

| 事件 | 描述 |
|-------|-------------|
| `step_start` | 步骤开始执行 |
| `step_end` | 步骤执行完成 |
| `tool_call` | AI Agent 调用了工具 |
| `tool_result` | 工具返回了结果 |
| `screenshot` | 截取了屏幕截图 |
| `error` | 发生了错误 |
