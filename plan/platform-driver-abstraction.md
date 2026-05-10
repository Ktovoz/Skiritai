# Platform Driver Abstraction — 问题分析与重构方案

## 1. 当前问题

Skiritai 当前的架构完全围绕 **Playwright 浏览器自动化** 构建，从核心层到工具层，浏览器相关代码与框架深度耦合，无法扩展到其他平台（API、Mobile、Desktop 等）。

### 1.1 耦合点清单

| 模块 | 文件 | 耦合表现 |
|------|------|----------|
| **BaseCase** | `core/base_case.py:10` | 直接 `from playwright.async_api import async_playwright, Browser, BrowserContext, Page` |
| **BaseCase** | `core/base_case.py:187-189` | 实例变量硬编码为 `_browser: Browser`, `_context: BrowserContext`, `_page: Page` |
| **BaseCase** | `core/base_case.py:246` | `async_playwright().start()` 内联在 `launch_browser()` 中 |
| **BaseCase** | `core/base_case.py:206` | `page` 属性返回类型为 `Page`（Playwright 类型） |
| **BaseCase** | `core/base_case.py:442` | `_make_ai()` 将 `self.page`（Playwright Page）传给 AIContext |
| **AIContext** | `core/ai_context.py:33` | 构造函数接收 `page: Any`，实际为 Playwright Page |
| **AIContext** | `core/ai_context.py:103` | `_replay()` 中 `exec_globals["run"](self.page, self.page.context)` 直接传 Playwright 对象 |
| **AIContext** | `core/ai_context.py:124` | `_explore()` 调用 `run_agent(page=self.page, ...)` |
| **CaseContext** | `core/case_context.py:106-131` | `BrowserSessionInfo` 包含 `cdp_port`, `pid`，纯浏览器概念 |
| **CaseContext** | `core/case_context.py:160` | `self.browser = BrowserSessionInfo()` 作为固定子组件 |
| **Tools** | `core/tools.py:11` | `_page_ctx` 存储的是 Playwright Page |
| **Tools** | `core/tools.py:28-269` | 全部 14 个工具直接调用 Playwright API（`page.goto`, `page.locator`, `page.click` 等） |
| **Perception** | `core/perception.py:53` | `from browser_use.browser.session import BrowserSession` 硬编码 |
| **Perception** | `core/perception.py:80` | `DomService` 依赖浏览器 DOM 树 |
| **Agent Loop** | `core/agent_loop.py:24` | `DEFAULT_SYSTEM_PROMPT` 硬编码为"浏览器自动化测试 Agent" |
| **Agent Loop** | `core/agent_loop.py:142` | `run_agent(page: Any)` 接收 Playwright Page，调用 `set_page(page)` |
| **Agent Loop** | `core/agent_loop.py:89-96` | `register_all_tools()` 只注册了浏览器工具 |
| **Script Gen** | `core/script_generator.py:41` | 生成的 replay 脚本固定 `from playwright.async_api import async_playwright` |
| **Script Gen** | `core/script_generator.py:68-116` | `_action_to_line()` 只能生成 Playwright API 调用 |

### 1.2 影响分析

由于上述耦合，以下场景**完全无法实现**：

- **API 测试** — 无法发送 HTTP 请求、验证响应状态码/JSON schema
- **Mobile 测试** — 无法连接 Appium/Device Farm，无法执行 tap/swipe/scroll 等移动端操作
- **Desktop 测试** — 无法自动化 Electron/原生应用
- **混合测试** — 无法在一个 Case 中组合多种平台（如：调用 API → 验证 Web 页面 → 检查 Mobile 推送）
- **自定义平台扩展** — 用户无法通过插件机制添加新平台支持

### 1.3 当前架构中已具备的良好抽象

以下模块已经做到了较好的解耦，可以作为重构的参考模式：

| 模块 | 设计模式 | 说明 |
|------|----------|------|
| `llm/` | ABC + 注册表 | `LLMProvider` 抽象基类 + `register_provider()` 注册表，支持 OpenAI/Anthropic 扩展 |
| `events/` | 发布-订阅 | `EventBus` 解耦了执行引擎和传输层（WebSocket） |
| `tool_registry.py` | 注册表 + 装饰器 | `@register_tool` 自动注册，支持 singleton 和 isolated 模式 |
| `case_context.py` | 状态机 | `CasePhase` 状态机本身是平台无关的 |

---

## 2. 解决方案：Platform Driver 抽象层

### 2.1 目标架构

```
┌──────────────────────────────────────────────────────┐
│               BaseCase / AIContext                    │  框架核心（平台无关）
│  - 步骤发现、生命周期、Hooks、失败策略                  │
│  - self.ai.action("描述")                             │
├──────────────────────────────────────────────────────┤
│            PlatformDriver (ABC)                       │  平台驱动抽象接口
│  - launch() / close()                                │
│  - get_tools() -> list[Tool]                         │
│  - get_perception_tools() -> list[Tool]              │
│  - get_system_prompt() -> str                        │
│  - get_session_info() -> SessionInfo                 │
│  - generate_replay_script(steps) -> str              │
│  - get_target() -> Any                               │
├────────────┬──────────────┬──────────────────────────┤
│  Browser   │     API      │       Mobile             │  具体实现
│ (Playwright)│   (httpx)    │     (Appium)             │
│  tools:    │   tools:     │     tools:               │
│  navigate  │   http_get   │     tap                  │
│  click     │   http_post  │     swipe                │
│  fill      │   assert_    │     input_text           │
│  ...       │   status     │     find_element         │
│            │   ...        │     ...                  │
├────────────┴──────────────┴──────────────────────────┤
│              ToolRegistry (已有)                       │  按平台注册工具集
├──────────────────────────────────────────────────────┤
│              Agent Loop (已有)                         │  ReAct Agent（平台无关）
├──────────────────────────────────────────────────────┤
│              LLM Provider (已有)                       │  OpenAI / Anthropic（平台无关）
├──────────────────────────────────────────────────────┤
│              EventBus (已有)                           │  发布-订阅（平台无关）
└──────────────────────────────────────────────────────┘
```

### 2.2 PlatformDriver 抽象接口

```python
# skiritai/drivers/base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from langchain_core.tools import Tool


class SessionInfo:
    """平台无关的会话信息（替代 BrowserSessionInfo）。"""
    platform: str              # "browser" | "api" | "mobile" | ...
    mode: str                  # "standard" | "persistent" | ...
    started_at: float | None
    extra: dict[str, Any]      # 平台特有信息（如 cdp_port, pid, device_id 等）


class PlatformDriver(ABC):
    """平台驱动抽象基类。
    
    每个平台（Browser、API、Mobile）实现此接口，
    为框架提供统一的工具集、感知能力、系统提示和脚本生成能力。
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台标识，如 "browser", "api", "mobile"。"""

    @abstractmethod
    async def launch(self, **kwargs) -> None:
        """启动平台会话（如启动浏览器、创建 HTTP Session、连接设备）。"""

    @abstractmethod
    async def close(self) -> None:
        """关闭平台会话并释放资源。"""

    @abstractmethod
    def get_target(self) -> Any:
        """获取平台的主操作对象（Playwright Page / httpx.AsyncClient / Appium Driver）。"""

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """返回该平台的操作工具集（如 click/fill 或 http_get/http_post）。"""

    def get_perception_tools(self) -> list[Tool]:
        """返回该平台的感知/只读工具集。默认为空列表。"""
        return []

    def get_system_prompt(self) -> str:
        """返回该平台的 AI Agent 系统提示。可由子类覆盖。"""
        return "你是一个自动化测试 Agent。"

    def get_session_info(self) -> SessionInfo:
        """返回当前会话信息。"""
        return SessionInfo(platform=self.platform_name)

    def generate_replay_script(self, step_id: str, steps: list[dict]) -> str:
        """根据工具调用历史生成 replay 脚本。"""
        raise NotImplementedError(
            f"Platform {self.platform_name} does not support replay script generation"
        )

    @property
    def supports_replay(self) -> bool:
        """该平台是否支持 replay 脚本生成。"""
        return False
```

### 2.3 Browser Driver 实现（迁移现有代码）

```python
# skiritai/drivers/browser.py

class BrowserDriver(PlatformDriver):
    """浏览器平台驱动 — 基于 Playwright + browser-use。"""

    platform_name = "browser"

    def __init__(self, case_dir: Path, headless: bool | None = None):
        self._case_dir = case_dir
        self._headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    async def launch(self, **kwargs):
        # 迁移自 BaseCase.launch_browser()

    async def close(self):
        # 迁移自 BaseCase.close_browser()

    def get_target(self) -> Page:
        return self._page

    def get_tools(self) -> list[Tool]:
        """注册并返回浏览器操作工具。"""
        from skiritai.drivers.browser_tools import register_browser_tools
        return register_browser_tools()

    def get_perception_tools(self) -> list[Tool]:
        """返回 browser-use 感知工具。"""
        from skiritai.drivers.browser_perception import register_perception_tools
        return register_perception_tools()

    def get_system_prompt(self) -> str:
        return DEFAULT_BROWSER_PROMPT  # 当前的 DEFAULT_SYSTEM_PROMPT

    def generate_replay_script(self, step_id: str, steps: list[dict]) -> str:
        # 迁移自 script_generator.py
        ...

    @property
    def supports_replay(self) -> bool:
        return True
```

### 2.4 API Driver 实现（新增）

```python
# skiritai/drivers/api.py

class ApiDriver(PlatformDriver):
    """API 测试平台驱动 — 基于 httpx。"""

    platform_name = "api"

    def __init__(self, base_url: str = "", headers: dict | None = None):
        self._base_url = base_url
        self._headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def launch(self, **kwargs):
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()

    def get_target(self) -> httpx.AsyncClient:
        return self._client

    def get_tools(self) -> list[Tool]:
        """返回 API 测试工具集。"""
        return [
            http_get,        # GET 请求
            http_post,       # POST 请求
            http_put,        # PUT 请求
            http_delete,     # DELETE 请求
            assert_status,   # 断言响应状态码
            assert_json,     # 断言 JSON 响应字段
            assert_header,   # 断言响应头
            set_header,      # 设置全局请求头（如 Authorization）
        ]
```

### 2.5 Mobile Driver 实现（新增）

```python
# skiritai/drivers/mobile.py

class MobileDriver(PlatformDriver):
    """移动端测试平台驱动 — 基于 Appium。"""

    platform_name = "mobile"

    def __init__(self, capabilities: dict):
        self._caps = capabilities
        self._driver = None

    async def launch(self, **kwargs):
        from appium.webdriver import AsyncWebDriver
        self._driver = await AsyncWebDriver(self._caps)

    async def close(self):
        if self._driver:
            await self._driver.quit()

    def get_tools(self) -> list[Tool]:
        return [
            tap,             # 点击坐标/元素
            swipe,           # 滑动
            input_text,      # 输入文本
            find_element,    # 查找元素
            press_key,       # 按键
            get_page_source, # 获取 UI 树
        ]
```

### 2.6 Driver 注册表

```python
# skiritai/drivers/registry.py

_driver_registry: dict[str, type[PlatformDriver]] = {}

def register_driver(name: str, driver_cls: type[PlatformDriver]) -> None:
    _driver_registry[name] = driver_cls

def get_driver(name: str) -> type[PlatformDriver]:
    if name not in _driver_registry:
        raise ValueError(f"Unknown driver: {name}. Available: {list(_driver_registry.keys())}")
    return _driver_registry[name]

# 内置驱动自动注册
register_driver("browser", BrowserDriver)
register_driver("api", ApiDriver)
register_driver("mobile", MobileDriver)
```

---

## 3. 框架核心层改造

### 3.1 BaseCase 改造

**改动前：**
```python
class BaseCase:
    def __init__(self, ...):
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page: ...

    async def launch_browser(self): ...
    async def close_browser(self): ...
```

**改动后：**
```python
class BaseCase:
    driver: PlatformDriver | None = None  # 子类可声明使用的驱动类型

    def __init__(self, ...):
        self._driver: PlatformDriver | None = None

    @property
    def target(self) -> Any:
        """平台主操作对象（Browser Page / HTTP Client / Mobile Driver）。"""
        if self._driver is None:
            raise RuntimeError("Driver not initialized. Call setup() first.")
        return self._driver.get_target()

    # 向后兼容：保留 page 属性，但委托给 driver
    @property
    def page(self) -> Any:
        """向后兼容：Browser 平台返回 Playwright Page，其他平台报错。"""
        return self.target

    async def setup(self):
        """子类覆盖，指定驱动并启动。"""
        pass

    async def teardown(self):
        if self._driver:
            await self._driver.close()
```

### 3.2 CaseContext 改造

**改动前：**
```python
class CaseContext:
    self.browser = BrowserSessionInfo()  # 硬编码浏览器
```

**改动后：**
```python
class CaseContext:
    def __init__(self, ...):
        self.session = SessionInfo()  # 通用会话信息
        # self.browser 保留为向后兼容属性，委托给 session
```

### 3.3 AIContext 改造

**改动前：**
```python
class AIContext:
    def __init__(self, page: Any, ...):
        self.page = page
```

**改动后：**
```python
class AIContext:
    def __init__(self, driver: PlatformDriver, ...):
        self._driver = driver

    @property
    def page(self) -> Any:
        """向后兼容。"""
        return self._driver.get_target()
```

### 3.4 ToolRegistry 改造

当前 `register_all_tools()` 硬编码注册浏览器工具：

```python
def register_all_tools() -> None:
    import skiritai.core.tools       # 浏览器操作工具
    import skiritai.core.perception  # 浏览器感知工具
```

**改动后：**
```python
def register_tools_for_driver(driver: PlatformDriver) -> None:
    """根据平台驱动注册对应的工具集。"""
    registry = ToolRegistry()
    registry.clear()

    for tool in driver.get_tools():
        registry.register(tool)
    for tool in driver.get_perception_tools():
        registry.register(tool)
```

### 3.5 Agent Loop 改造

**改动前：**
```python
async def run_agent(page: Any, ...):
    set_page(page)  # 绑定 Playwright Page
```

**改动后：**
```python
async def run_agent(driver: PlatformDriver, ...):
    register_tools_for_driver(driver)
    system_prompt = driver.get_system_prompt()
    # agent 构建和执行逻辑不变 — ReAct Agent 本身是平台无关的
```

### 3.6 Script Generator 改造

将脚本生成委托给 `PlatformDriver`：

```python
# ai_context.py — _explore()
if result.get("success") and driver.supports_replay:
    script = driver.generate_replay_script(self.step_id, result.get("steps", []))
    self.script_path.write_text(script, encoding="utf-8")
```

---

## 4. 用户使用方式

### 4.1 Browser Case（向后兼容）

```python
from skiritai import BaseCase
from skiritai.drivers.browser import BrowserDriver

class MyWebCase(BaseCase):
    driver = BrowserDriver(headless=True)

    async def setup(self):
        await self._driver.launch()

    async def search(self):
        await self.ai.action("搜索关键词")
```

或通过便捷基类：

```python
from skiritai import BrowserCase  # 内置便捷类，等同于上面

class MyWebCase(BrowserCase):
    async def search(self):
        await self.ai.action("搜索关键词")
```

### 4.2 API Case（新增）

```python
from skiritai import BaseCase
from skiritai.drivers.api import ApiDriver

class MyApiCase(BaseCase):
    driver = ApiDriver(base_url="https://api.example.com")

    async def setup(self):
        await self._driver.launch()

    async def create_user(self):
        await self.ai.action("POST /users 创建一个新用户，name=test, email=test@example.com")

    async def verify_user(self):
        await self.ai.action("GET /users/1 验证用户信息正确")
```

### 4.3 Mobile Case（新增）

```python
from skiritai import BaseCase
from skiritai.drivers.mobile import MobileDriver

class MyMobileCase(BaseCase):
    driver = MobileDriver(capabilities={
        "platformName": "iOS",
        "deviceName": "iPhone 15",
    })

    async def setup(self):
        await self._driver.launch()

    async def login(self):
        await self.ai.action("在登录页面输入用户名和密码，点击登录按钮")
```

### 4.4 混合 Case（多平台组合）

```python
from skiritai import BaseCase
from skiritai.drivers.browser import BrowserDriver
from skiritai.drivers.api import ApiDriver

class MixedCase(BaseCase):
    async def setup(self):
        self.api = ApiDriver(base_url="https://api.example.com")
        self.web = BrowserDriver()
        await self.api.launch()
        await self.web.launch()

    async def prepare_data(self):
        # 通过 API 准备数据
        await self.api.action("POST /users 创建测试用户")

    async def verify_ui(self):
        # 切换到浏览器验证
        self._driver = self.web
        await self.ai.action("打开用户列表页面，验证新用户显示正确")
```

---

## 5. 目录结构变化

### 改动前

```
skiritai/core/
├── base_case.py          # BaseCase + 浏览器生命周期
├── tools.py              # 14 个 Playwright 工具
├── perception.py         # browser-use DOM 感知
├── browser.py            # Playwright 浏览器管理
├── script_generator.py   # Playwright replay 脚本生成
├── ai_context.py         # AIContext（绑定 Playwright Page）
├── agent_loop.py         # Agent 循环（绑定 Playwright 工具）
├── tool_registry.py      # 工具注册表
├── case_context.py       # CaseContext + BrowserSessionInfo
```

### 改动后

```
skiritai/
├── core/                          # 框架核心（平台无关）
│   ├── base_case.py               # BaseCase（通过 PlatformDriver 管理）
│   ├── ai_context.py              # AIContext（通过 PlatformDriver 操作）
│   ├── agent_loop.py              # Agent 循环（动态加载平台工具）
│   ├── tool_registry.py           # 工具注册表（不变）
│   ├── case_context.py            # CaseContext + SessionInfo（通用）
│   ├── runner.py                  # Case 发现和执行（不变）
│   ├── execution_manager.py       # 执行管理（不变）
│   └── llm_retry.py              # LLM 重试（不变）
│
├── drivers/                       # 平台驱动层（新增目录）
│   ├── __init__.py                # 公共 API + 注册表
│   ├── base.py                    # PlatformDriver ABC + SessionInfo
│   ├── registry.py                # Driver 注册表（类似 LLM Provider 注册）
│   │
│   ├── browser/                   # 浏览器平台
│   │   ├── __init__.py
│   │   ├── driver.py              # BrowserDriver
│   │   ├── tools.py               # 迁移自 core/tools.py
│   │   ├── perception.py          # 迁移自 core/perception.py
│   │   ├── browser.py             # 迁移自 core/browser.py
│   │   └── script_generator.py    # 迁移自 core/script_generator.py
│   │
│   ├── api/                       # API 测试平台（新增）
│   │   ├── __init__.py
│   │   ├── driver.py              # ApiDriver
│   │   └── tools.py               # HTTP 工具集
│   │
│   └── mobile/                    # 移动端平台（新增）
│       ├── __init__.py
│       ├── driver.py              # MobileDriver
│       └── tools.py               # Appium 工具集
```

---

## 6. 实施计划

### Phase 1：抽象层 + Browser 迁移（最小可行变更）

**目标**：引入 `PlatformDriver` 抽象，将现有浏览器代码迁移到 `BrowserDriver`，确保所有现有用例不 break。

**改动清单**：
1. 新建 `drivers/base.py` — 定义 `PlatformDriver` ABC 和 `SessionInfo`
2. 新建 `drivers/registry.py` — Driver 注册表
3. 新建 `drivers/browser/` — 从 `core/` 迁移浏览器相关代码
4. 改造 `core/base_case.py` — 持有 `PlatformDriver` 而非 Playwright 对象
5. 改造 `core/ai_context.py` — 接收 `PlatformDriver` 而非 `page`
6. 改造 `core/agent_loop.py` — 动态注册平台工具
7. 改造 `core/case_context.py` — `BrowserSessionInfo` → `SessionInfo`
8. 提供 `BrowserCase` 便捷基类，确保向后兼容
9. 所有现有测试通过

**验证标准**：
- 所有现有 examples 无需修改即可运行（或仅需 `import` 路径调整）
- `BrowserCase` 向后兼容 `BaseCase` 的所有浏览器方法
- 新的 `PlatformDriver` 接口可通过类型检查

### Phase 2：API Driver

**目标**：实现 API 测试平台支持。

**改动清单**：
1. 新建 `drivers/api/` — `ApiDriver` + HTTP 工具集
2. API 工具：`http_get`, `http_post`, `http_put`, `http_delete`, `assert_status`, `assert_json`, `assert_header`, `set_header`
3. API 系统提示词
4. 示例 Case 和文档

**验证标准**：
- 可编写纯 API 测试 Case
- AI Agent 可通过 HTTP 工具完成 API 测试任务
- API 测试支持 replay 脚本生成

### Phase 3：Mobile Driver

**目标**：实现移动端测试平台支持。

**改动清单**：
1. 新建 `drivers/mobile/` — `MobileDriver` + Appium 工具集
2. Mobile 工具：`tap`, `swipe`, `input_text`, `find_element`, `press_key`, `get_page_source`
3. Mobile 感知层：UI 树解析（类比浏览器 DOM 感知）
4. Mobile 系统提示词
5. 示例 Case 和文档

### Phase 4：混合模式 + 生态完善

**目标**：支持多平台组合、自定义 Driver 扩展。

**改动清单**：
1. `MultiDriver` — 在单个 Case 中组合多个 PlatformDriver
2. `driver.switch_to("api")` — 运行时切换活跃驱动
3. 自定义 Driver 扩展文档和开发者指南
4. 第三方 Driver 注册机制（类似 LLM Provider）

---

## 7. 风险与注意事项

| 风险 | 缓解措施 |
|------|----------|
| **向后兼容性破坏** | Phase 1 中保留 `self.page`、`launch_browser()` 等旧 API 作为兼容层，标记为 deprecated |
| **工具命名冲突** | 不同平台的工具可能有相同名称（如 `find_element`），使用命名空间前缀或按平台注册 |
| **依赖膨胀** | API Driver 使用 `httpx`（已常用于测试），Mobile Driver 的 `appium` 设为可选依赖 `[mobile]` |
| **测试覆盖** | Phase 1 必须确保所有现有测试通过后才进入 Phase 2 |
| **Replay 脚本兼容** | 旧格式 replay 脚本需要向后兼容，或提供迁移工具 |

---

## 8. 总结

当前 Skiritai 的核心问题是**缺乏平台抽象层**，导致 Playwright 浏览器代码与框架核心深度耦合。解决方案的核心是引入 `PlatformDriver` 抽象接口，将平台相关代码（工具、感知、脚本生成、生命周期）从核心层剥离到独立的 Driver 模块中。

这种设计与框架已有的 `LLMProvider` 抽象模式一脉相承，保持了架构风格的一致性。实施上采用渐进式策略，先完成抽象层和 Browser 迁移（Phase 1），再逐步添加 API 和 Mobile 支持。
