# 浏览器会话

Skiritai 支持两种浏览器模式：**标准模式**（进程内）和**持久化模式**（基于 CDP，Python 重启后依然存活）。

## 标准模式

默认模式。浏览器作为 Python 进程的一部分运行，进程退出时销毁。

```python
class MyTest(BaseCase):
    async def setup(self):
        await self.launch_browser()   # 默认：标准模式

    async def teardown(self):
        await self.close_browser()
```

## 持久化模式

浏览器通过 Chrome DevTools Protocol (CDP) 以**独立子进程**方式启动。Python 重启、崩溃、断连后依然存活。可随时断开和重连。

```python
class MyTest(BaseCase):
    async def setup(self):
        await self.launch_browser_persistent()  # CDP 子进程

    async def teardown(self):
        await self.disconnect_browser()         # 断开，浏览器保持运行
```

### 核心优势

- **跨重启存活** — 浏览器进程的生命周期独立于 Python 脚本
- **跨进程重连** — 在一个进程中启动，从另一个进程重连
- **状态保留** — 页面、cookie、localStorage 在连接间持久化
- **CI 友好清理** — `atexit` 处理器在正常退出时自动终止孤儿进程

## CDP 架构

```
Python 进程              浏览器子进程
┌──────────┐     CDP    ┌──────────────┐
│ Playwright │ ←────────→│  Chromium     │
│   + CDP   │  ws://    │  --remote-    │
│  client   │           │  debugging-   │
│           │           │  port=9222    │
└──────────┘           └──────────────┘
         │                     │
         .browser_session     会话文件持久化在磁盘上
         (cdp_port + pid)
```

会话文件 `.browser_session` 存储 CDP 端口和 PID，其他进程可通过它找到浏览器。

## 生命周期 API

### 完整控制

```python
# Setup（首次运行）
await self.launch_browser_persistent()   # 启动 Chromium 子进程
# ... 运行步骤 ...

# 断开（浏览器保持运行）
await self.disconnect_browser()          # Python 退出，浏览器保留

# 重连（之后，可能在不同的脚本中）
await self.reconnect_browser()           # 通过持久化的 CDP 端口重新连接
# ... 运行更多步骤 ...

# Teardown（最终）
await self.terminate_browser()           # 终止浏览器，清理会话文件
```

### 标准模式（非持久化）

```python
await self.launch_browser()              # 进程内浏览器
await self.close_browser()               # 关闭浏览器
```

## CLI 会话管理

```bash
# 检查用例的持久化浏览器是否在运行
skiritai browser status <case_dir>

# 终止持久化浏览器并清理会话文件
skiritai browser cleanup <case_dir>
```

## 会话文件

存储在 `<case_dir>/.browser_session`：

```json
{
  "cdp_port": 9222,
  "pid": 48291
}
```

## 编程检查

```python
# 检查会话文件是否存在
self.has_browser_session()    # .browser_session 存在时为 True

# 检查浏览器进程是否存活
from skiritai.core.browser import is_browser_alive
is_browser_alive(case_dir)

# 加载会话信息
from skiritai.core.browser import load_session
session = load_session(case_dir)  # {"cdp_port": 9222, "pid": 48291}
```

## CI / 无头模式

为 CI 环境设置环境变量：

```bash
SKIRITAI_HEADLESS=true       # 无头模式
CI=true                      # 自动添加 --no-sandbox 标志
SKIRITAI_CHROME_PATH=/path   # 自定义 Chromium 路径
```
