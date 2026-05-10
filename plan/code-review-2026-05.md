# Skiritai Code Review — 2026-05

> 审查范围：全量源码（core、llm、events、web、cli），不含文档和测试用例。
> 审查目标：发现安全风险、架构瓶颈、正确性缺陷、可维护性和性能问题。

---

## 目录

- [一、安全问题（P0）](#一安全问题p0)
- [二、架构与设计问题（P1）](#二架构与设计问题p1)
- [三、功能与健壮性问题（P1-P2）](#三功能与健壮性问题p1-p2)
- [四、代码质量与可维护性（P2-P3）](#四代码质量与可维护性p2-p3)
- [五、性能优化（P3）](#五性能优化p3)
- [六、优先级总览](#六优先级总览)

---

## 一、安全问题（P0）

### 1. `exec()` 执行回放脚本存在严重安全隐患

**文件**: `skiritai/core/ai_context.py:100`

```python
exec(script_content, exec_globals)
```

回放脚本由 AI 生成并存储在磁盘上，执行时直接调用 `exec()`。如果脚本被篡改（供应链攻击、磁盘权限问题），等同于执行任意代码。

**建议**:

- 保存脚本时计算并记录内容的 SHA-256 hash，执行前校验完整性
- 限制 `exec_globals["__builtins__"]`，只暴露必要的内置函数（如 `None`, `True`, `False`）
- 长期方案：用 AST 白名单解析，只允许 `await page.xxx(...)` 形式的调用

```python
# 示例：保存时记录 hash
import hashlib
script_hash = hashlib.sha256(script.encode()).hexdigest()
(script_path.with_suffix(".sha256")).write_text(script_hash)

# 执行前校验
saved_hash = (self.script_path.with_suffix(".sha256")).read_text().strip()
actual_hash = hashlib.sha256(script_content.encode()).hexdigest()
if saved_hash != actual_hash:
    raise RuntimeError(f"Script integrity check failed for {self.step_id}")
```

### 2. `eval_js` 工具允许执行任意 JavaScript

**文件**: `skiritai/core/tools.py:159`

```python
result = await page.evaluate(expression)
```

AI agent 可以通过此工具执行任意 JavaScript，包括读取 Cookie、修改 DOM、发起网络请求等。

**建议**:

- 在文档中明确标注安全边界和使用风险
- 短期：添加可选的 JS 执行开关（环境变量 `SKIRITAI_ALLOW_EVAL_JS=false`）
- 长期：集成 CDP 沙箱或 Content Security Policy 限制

### 3. 截图文件路径遍历风险

**文件**: `skiritai/web/routers/cases.py:286-287`

```python
if ".." in filename or "/" in filename:
    raise HTTPException(status_code=400, detail="Invalid filename")
```

只检查了 `..` 和 `/`，未覆盖以下情况：

- Windows 路径分隔符 `\`
- URL 编码（如 `%2e%2e%2f`）
- 空字节注入（如 `..\0.png`）

**建议**: 使用 `Path.resolve()` + `is_relative_to()` 做严格路径校验：

```python
screenshots_base = (CASES_ROOT / case_id / "test_results" / timestamp / "screenshots").resolve()
screenshot_path = (screenshots_base / filename).resolve()
if not screenshot_path.is_relative_to(screenshots_base):
    raise HTTPException(status_code=400, detail="Invalid filename")
if not screenshot_path.exists():
    raise HTTPException(status_code=404, detail="Screenshot not found")
return FileResponse(screenshot_path, media_type="image/png")
```

---

## 二、架构与设计问题（P1）

### 4. 版本号不一致

**文件对比**:

| 文件 | 版本 |
|------|------|
| `pyproject.toml` | `0.0.3` |
| `skiritai/__init__.py:37` | `0.0.2` |

**建议**: 从 package metadata 动态读取，保持单一数据源：

```python
# skiritai/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("skiritai")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
```

### 5. 单例 ToolRegistry 的全局状态耦合

**文件**: `skiritai/core/tool_registry.py`

`ToolRegistry` 通过 `__new__` 实现单例，`@register_tool` 装饰器在模块导入时自动注册到全局单例。这导致：

- 测试隔离困难（需要手动 `reset_singleton()`）
- 导入顺序影响注册结果
- `create_isolated()` 创建的实例无法被 `@register_tool` 使用
- Web 模式下多个并发 case 共享同一注册表

**建议**:

- 短期：确保 `register_all_tools()` 被正确调用，在 `build_agent()` 中添加工具数量断言
- 长期：改为在 `build_agent()` 时显式传入工具列表，而非依赖导入副作用注册：

```python
def build_agent(system_prompt, tools=None):
    if tools is None:
        tools = collect_default_tools()  # 显式收集
    return create_react_agent(model=llm, tools=tools, prompt=system_prompt)
```

### 6. contextvars 在并发场景下的冲突风险

**文件**: `skiritai/core/tools.py:11`

```python
_page_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("_page_ctx", default=None)
```

`set_page()` 设置的 page 是全局 contextvar。Web 模式下如果并发执行多个 case，不同 case 的 `set_page()` 调用会互相覆盖，导致工具操作错误的页面。

**建议**:

- 短期：在 `run_case()` 中加锁（`asyncio.Lock`），确保同一时间只有一个 case 在执行
- 长期：将 page 通过参数传递而非 contextvar，或使用 per-case 的 context：

```python
# 方案 A：加锁
_case_lock = asyncio.Lock()

async def run_case(case_dir, ...):
    async with _case_lock:
        ...

# 方案 B：per-case context（推荐）
# 将 page 绑定到 AIContext 实例，工具函数从 AIContext 获取 page
```

### 7. `BaseCase.run()` 方法过长

**文件**: `skiritai/core/base_case.py:580-692`（约 110 行）

`run()` 包含了 setup phase、step 循环（含重试逻辑、failure policy 判断）、teardown phase、报告生成和保存。职责过多，难以单独测试和阅读。

**建议**: 拆分为独立方法：

```python
async def run(self) -> dict:
    report = await self._run_lifecycle()
    self._save_report(report)
    return report

async def _run_lifecycle(self) -> dict:
    await self._run_setup()
    await self._run_steps()
    await self._run_teardown()
    return self._build_report(...)

async def _run_steps(self) -> None:
    steps = self.get_step_methods()
    for step_name in steps:
        await self._run_single_step(step_name)

async def _run_single_step(self, step_name: str) -> None:
    policy, max_retries = self._get_step_failure_policy(step_name)
    # ... 重试逻辑
```

### 8. `_build_report` 重复调用 `get_step_methods()`

**文件**: `skiritai/core/base_case.py:696`

```python
def _build_report(self, status, error=None):
    total = len(self.get_step_methods())  # 每次构建报告都重新计算
```

而 `run()` 方法开头已经调用过 `get_step_methods()`。每次都重新遍历 `dir(self)` 做反射，虽然性能影响不大，但语义上不必要。

**建议**: 在 `run()` 开头缓存 steps 到 `self._steps`，后续直接使用。

---

## 三、功能与健壮性问题（P1-P2）

### 9. 回放脚本的 `_esc()` 转义不完整

**文件**: `skiritai/core/script_generator.py:120-132`

手写的 `_esc()` 只处理了 `\`、`"`、`\n`、`\r`、`\t`，遗漏了：

- `$` 符号（在 f-string 或 shell 中有特殊含义）
- Unicode 控制字符
- 三引号 `"""` 序列

**建议**: 统一使用 `repr()` 或 `json.dumps()` 做转义。`eval_js` 的处理已经用了 `repr()`（正确做法），应推广到所有参数：

```python
# 替换所有 _esc() 调用
if action == "click":
    selector = args.get("selector", "")
    return f"    await page.click({json.dumps(selector)})"
```

### 10. `_hook_result` 泄漏到外部结果中

**文件**: `skiritai/core/base_case.py:540`

```python
result = {"success": False, "summary": str(e), "_hook_result": hook_result}
```

`_hook_result` 是 `StepResult` 对象，包含在返回结果中，传递给了 event 和 report。这导致：

- `on_step_error` hook 的内部决策暴露给外部
- report 的 JSON 序列化可能出现问题（`StepResult` 不是 JSON-serializable）
- 调用方需要知道 `_hook_result` 的存在才能正确处理

**建议**: 使用独立通道传递 hook 结果：

```python
# 在 run_step 内部
self._last_hook_result = hook_result
result = {"success": False, "summary": str(e)}

# 在 run() 中
result = await self.run_step(step_name)
hook_result = self._last_hook_result
```

### 11. EventBus `publish()` 串行等待所有 handler

**文件**: `skiritai/events/__init__.py:135`

```python
for handler in handlers:
    await handler(event)
```

如果某个 handler 阻塞或耗时较长（如 WebSocket 发送超时），会拖慢事件发布，进而阻塞 case 执行。

**建议**:

- 短期：用 `asyncio.gather()` 并发执行
- 长期：用 `asyncio.create_task()` 做即发即弃，handler 内部自行处理错误

```python
async def publish(self, event: Event) -> None:
    self._append_history(event)
    self._persist_event(event)
    handlers = list(self._all_handlers) + self._handlers.get(event.type, [])
    results = await asyncio.gather(
        *[self._safe_call(h, event) for h in handlers],
        return_exceptions=True,
    )
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"[EventBus] Handler error: {r}")

async def _safe_call(self, handler, event):
    try:
        await handler(event)
    except Exception as e:
        logger.error(f"[EventBus] Handler error for '{event.type}': {e}", exc_info=True)
```

### 12. `_wait_for_cdp` 使用同步阻塞 IO

**文件**: `skiritai/core/browser.py:149-168`

```python
def _wait_for_cdp(port, timeout=10.0) -> bool:
    # ...
    with urllib.request.urlopen(...) as resp:  # 同步阻塞
```

在 `async` 函数 `launch_browser_server` 中调用了同步的 `_wait_for_cdp`，会阻塞事件循环，导致其他 asyncio task（如 WebSocket 心跳、事件处理）停滞。

**建议**: 改用 `httpx.AsyncClient`：

```python
async def _wait_for_cdp(port: int, timeout: float = 10.0) -> bool:
    import httpx
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                resp = await client.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
                data = resp.json()
                if data.get("webSocketDebuggerUrl"):
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.3)
    return False
```

### 13. 缺少 case 执行超时机制

**文件**: `skiritai/core/execution_manager.py`

`ExecutionManager` 只记录了 `case_id → task` 的映射，没有超时自动取消。如果 AI agent 进入死循环（LangGraph recursion_limit 不一定可靠），case 可能永远不结束。

**建议**:

- 添加全局超时配置（环境变量 `SKIRITAI_CASE_TIMEOUT`，默认如 300 秒）
- 在 `register_execution()` 时用 `asyncio.wait_for()` 包装：

```python
async def _run_with_timeout(task, timeout):
    try:
        return await asyncio.wait_for(task, timeout=timeout)
    except asyncio.TimeoutError:
        task.cancel()
        raise

async def _run():
    # ...
    await asyncio.wait_for(run_case(...), timeout=CASE_TIMEOUT)
```

---

## 四、代码质量与可维护性（P2-P3）

### 14. `__init__.py` 导出了过多内部实现

**文件**: `skiritai/__init__.py`

`AIContext` 和 `ActionMode` 被导出为公开 API，但用户通常通过 `self.ai` 访问 AIContext，不需要直接导入。

**建议**:

- 保留导出但添加注释说明内部使用场景
- 或在 `__all__` 中区分 "stable API" 和 "advanced API"
- 文档中明确标注哪些是稳定的公开 API

### 15. 类型标注风格不统一

项目中混用了两种风格：

```python
# 风格 1（新式，Python 3.10+）
def foo(x: str | None) -> dict[str, Any]: ...

# 风格 2（旧式）
from typing import Optional, Dict
def foo(x: Optional[str]) -> Dict[str, Any]: ...
```

**建议**: 项目声明 `requires-python = ">=3.11"`，统一使用 `X | Y` 风格，移除 `typing` 中的 `Optional`、`Dict`、`List` 等旧式导入。

### 16. `find_element` 的匹配算法可优化

**文件**: `skiritai/core/perception.py:188-273`

当前匹配是纯文本子串 + CJK bigram，对于复杂自然语言描述（如"右上角的关闭按钮"、"提交表单后弹出的确认框"）效果有限。

**建议**:

- 短期：添加方位词（上下左右、top/bottom/left/right）特殊处理
- 中期：利用 LLM 做一次 "description → structured selector intent" 的转换
- 长期：用 embedding 相似度匹配（但需权衡延迟）

### 17. `_render_html` 用字符串 replace 生成 HTML

**文件**: `skiritai/core/base_case.py:720-764`

```python
html = html.replace("{{case_name}}", report["case_name"])
html = html.replace("{{status}}", report["status"].upper())
```

**问题**:

- 如果 step 内容中包含 `{{xxx}}` 字符串，会被误替换
- 字符串拼接效率不高
- HTML 注入风险（step summary 中的 `<script>` 标签等）

**建议**:

- 使用 Jinja2 或 `string.Template`
- 对用户数据做 HTML 转义（`html.escape()`）

```python
import html as html_mod

step_rows.append(
    f'<span class="step-summary">{html_mod.escape(summary)}</span>'
)
```

---

## 五、性能优化（P3）

### 18. `list_cases` 每次调用都重新 import 所有 case.py

**文件**: `skiritai/core/runner.py:70-90`

Web API 的 `GET /api/cases` 每次请求都会 `importlib` 动态加载所有 case 文件。case 数量多或 case.py 复杂时，延迟明显。

**建议**: 添加带 TTL 的缓存：

```python
import time

_cases_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 60  # 秒

def list_cases(cases_root: Path) -> list[dict]:
    cache_key = str(cases_root)
    cached = _cases_cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]
    # ... 原有逻辑
    _cases_cache[cache_key] = (time.time(), cases)
    return cases
```

### 19. EventBus 文件写入每次都 open/close

**文件**: `skiritai/events/__init__.py:196-201`

```python
with open(path, "a", encoding="utf-8") as f:
    f.write(line + "\n")
```

高频事件场景下，每次 publish 都打开和关闭文件句柄。

**建议**: 保持文件句柄打开，使用 buffered writer：

```python
def enable_persistence(self, persist_dir: Path) -> None:
    self._persist_dir = persist_dir
    persist_dir.mkdir(parents=True, exist_ok=True)
    self._file_handles: dict[str, io.TextIOWrapper] = {}

def _persist_event(self, event: Event) -> None:
    if self._persist_dir is None:
        return
    eid = event.execution_id
    if eid not in self._file_handles:
        path = self._persist_dir / f"{eid}.jsonl"
        self._file_handles[eid] = open(path, "a", encoding="utf-8")
    self._file_handles[eid].write(line + "\n")
    self._file_handles[eid].flush()
```

### 20. WebSocket broadcast 可以批量发送

**文件**: `skiritai/web/ws_manager.py:28-38`

当前每个 event 都触发一次 `broadcast()`，高频工具调用时消息量大。

**建议**: 添加可选的消息批处理（100ms 窗口内的消息合并发送），或用 `send_json()` 替代 `send_text(json.dumps(...))`。

---

## 六、优先级总览

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P0** | #1 | `exec()` 安全隐患 | 安全 |
| **P0** | #3 | 路径遍历风险 | 安全 |
| **P1** | #4 | 版本号不一致 | 正确性 |
| **P1** | #6 | contextvars 并发冲突 | 正确性 |
| **P1** | #10 | `_hook_result` 泄漏 | 正确性 |
| **P1** | #12 | EventBus handler 串行 | 性能/设计 |
| **P1** | #13 | 同步阻塞事件循环 | 性能 |
| **P2** | #2 | eval_js 安全边界 | 安全/文档 |
| **P2** | #5 | ToolRegistry 解耦 | 架构 |
| **P2** | #7 | `run()` 方法拆分 | 可维护性 |
| **P2** | #8 | 重复 `get_step_methods()` | 代码质量 |
| **P2** | #9 | `_esc()` 转义不完整 | 正确性 |
| **P2** | #13 | 缺少执行超时 | 健壮性 |
| **P2** | #14 | 公开 API 边界不清 | API 设计 |
| **P3** | #15 | 类型标注不统一 | 代码风格 |
| **P3** | #16 | find_element 匹配算法 | 功能增强 |
| **P3** | #17 | HTML 模板安全隐患 | 安全/代码质量 |
| **P3** | #18 | list_cases 缓存 | 性能 |
| **P3** | #19 | EventBus 文件 IO | 性能 |
| **P3** | #20 | WS 消息批处理 | 性能 |

---

## 附录：审查覆盖范围

| 模块 | 文件 | 状态 |
|------|------|------|
| core | `base_case.py` | 已审查 |
| core | `agent_loop.py` | 已审查 |
| core | `ai_context.py` | 已审查 |
| core | `tools.py` | 已审查 |
| core | `browser.py` | 已审查 |
| core | `case_context.py` | 已审查 |
| core | `runner.py` | 已审查 |
| core | `perception.py` | 已审查 |
| core | `script_generator.py` | 已审查 |
| core | `tool_registry.py` | 已审查 |
| core | `llm_retry.py` | 已审查 |
| core | `execution_manager.py` | 已审查（未单独列出问题） |
| llm | `base.py`, `registry.py` | 已审查 |
| events | `__init__.py` | 已审查 |
| web | `app.py`, `ws_manager.py`, `routers/cases.py` | 已审查 |
| cli | `cli.py` | 已审查 |
| 配置 | `pyproject.toml` | 已审查 |
