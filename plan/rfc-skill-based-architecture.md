# RFC: 基于节点的 Skill 动态绑定架构

> 状态：讨论中
> 日期：2026-05-15
> 关联 PR：#34（dismiss_overlay 工具 + SPA 容错 + 抖音搜索示例）

## 1. 背景

### 1.1 当前问题

在实现抖音精选搜索测试（PR #34）的过程中，我们暴露了两个框架层面的缺陷：

1. **弹窗遮挡**：抖音登录弹窗会拦截所有点击事件，需要在 action 描述中嵌入原始 JavaScript 代码来绕过——违背了自然语言测试的初衷
2. **SPA 导航崩溃**：抖音页面二次导航导致 `page.evaluate` 抛出 `Execution context was destroyed`，框架不认为该错误可重试

PR #34 通过以下方式解决了这两个问题：

- 新增 `dismiss_overlay()` 工具自动关闭弹窗
- 新增 `safe_evaluate()` 辅助函数处理 SPA 导航崩溃
- 增强 `navigate()` 的 networkidle 等待
- 让 Playwright 导航错误变为可重试

**但这只是治标。** 根本问题是：我们的工具设计没有做好关注点分离。

### 1.2 提示词长度困境

当前系统面临一个核心矛盾：

1. **提示词太短** → 模型不能很好地使用工具，因为工具的描述和使用方法不够清晰
2. **提示词太长** → 所有信息硬编码到每一个步骤中，导致每个步骤都携带冗余信息

这是一个零和博弈：要么牺牲工具使用质量，要么牺牲 token 效率。根本原因是所有工具的完整描述每次都无差别地传给 LLM，没有按需加载的机制。

**Skill 架构要解决的核心问题就是打破这个困境**：默认只提供简洁的工具声明，当 agent 决定使用某个工具时，再动态注入完整的使用指导和参考资料。

### 1.3 当前架构

```
create_react_agent(model, tools=全部20个工具)
```

所有 20 个工具的名称、描述、参数 schema 每次都完整地传给 LLM，无论当前步骤是否需要。这导致：

- **Prompt 臃肿**：工具列表约 600 tokens，每个 step 都带着
- **LLM 决策干扰**：不需要的工具在列表中增加了 LLM 选择错误的可能性
- **无法按需加载**：低频工具（如 `configure_browser`、`dismiss_overlay`）每次都占用空间

### 1.4 抖音场景的教训

抖音搜索的最终 step 结构：

```
open_homepage → dismiss_popup → verify_homepage → search_keyword → verify_search_results → check_user_profile
```

每个 step 内部的 agent loop 都会重新分析页面、选择工具。但实际上：

- 进入一个页面后，**只需要 analyze 一次**
- 后续多个连续操作可以**共享同一次 analyze 的结果**
- 拆分后的细粒度 step 不需要各自独立 analyze

## 2. 目标

1. **节点化**：每个 API 方法（`ai.action`、`ai.verify`、`ai.screenshot`）是一个独立节点，每个节点绑定自己的工具集
2. **动态工具绑定**：每个节点只绑定自己需要的工具集，navigate、wait 等是工具而非节点
3. **工具补全**：Screenshot 和 Verify 节点需要配套工具供模型调用（当前是无工具的纯 LLM/Playwright 调用）
4. **状态共享**：节点的分析结果存入全局 state，后续节点直接读取
5. **Prompt 精简**：LLM 每次只看到当前节点需要的工具
6. **自然语言回归**：所有 step 描述保持纯自然语言

## 3. 方案设计

### 3.1 节点定义

节点按**函数类型（API 方法）**划分，不是按操作类型。每个节点有自己**专属的基础工具集**，低频 Skill 按需追加。

| 节点 | 对应 API | 专属基础工具 | 职责 |
|------|---------|------------|------|
| **Action** | `ai.action()` | analyze_page, click, click_text, click_force, fill, type_text, press_key, hover, select_option, navigate, wait, scroll, dismiss_overlay | 执行页面操作，内置 analyze 感知页面 |
| **Verify** | `ai.verify()` | verify_tool（新建）| AI 断言验证，获取页面状态并判断 |
| **Screenshot** | `ai.screenshot()` | screenshot_tool（新建）| 截图，模型决定截图范围/方式 |
| **Browser Setting** | `ai.config()` | set_ignore_ssl, set_headless, set_viewport_size, inject_script（新建） | 配置浏览器运行参数（**运行时注入，不重启**） |
| **JS Console** | `ai.js()` | eval_js, eval_js_file（新建） | 聚焦 JavaScript 执行，更专注的沙箱 |

**关键变化**：
- 每个节点的工具是**专属的**——Browser Setting 的工具只管浏览器配置，JS Console 的工具只管 JS 执行
- `navigate`、`wait`、`scroll`、`dismiss_overlay` 是 Action 节点的基础工具，不是节点
- **Verify** 需要新建 `verify_tool`，让模型能主动获取页面状态做断言
- **Screenshot** 需要新建 `screenshot_tool`，让模型能选择截图范围（全页/元素/区域）
- **Browser Setting** 是新节点：浏览器参数配置（SSL、无头模式、窗口大小、启动脚本）。**关键约束**：所有工具必须是运行时注入（如 `page.add_init_script()`、CDP 协议），不能要求重启浏览器，因为浏览器启动流程是固定的
- **JS Console** 是新节点：从 Action 的 `eval_js` 拆出，聚焦 JS 执行场景

### 3.2 工作流示例

```
Browser Setting → Action A → Action B → Verify → Screenshot → Action C → JS Console → Verify
  ↑ 配置浏览器参数     ↑ 共享 analyze 结果                                          ↑ 执行 JS 脚本
```

对比当前架构：

```
configure_browser（全局工具）→ Action A（内部 analyze，含 eval_js）→ Verify（纯 LLM）→ ...
所有工具每次都传给 LLM
```

### 3.3 状态传递

```python
# Analyze 节点执行后，结果存入 state
state = {
    "page_analysis": { ... },     # analyze_page 的结果
    "page_info": { ... },         # get_page_info 的结果
    "last_analyzed_url": "...",   # 上次 analyze 时的 URL
}

# Action 节点执行时，读取 state
# 如果当前 URL != last_analyzed_url，自动触发重新 analyze
```

### 3.4 动态工具绑定

```python
# 每个节点类型绑定自己的专属工具集
ACTION_TOOLS = [
    analyze_page, click, click_text, click_force, fill, type_text,
    press_key, hover, select_option, navigate, wait, scroll,
    dismiss_overlay,
]

VERIFY_TOOLS = [verify_tool]           # 获取页面状态 + 断言

SCREENSHOT_TOOLS = [screenshot_tool]   # 截图范围/方式选择

BROWSER_SETTING_TOOLS = [              # 浏览器配置专属工具（运行时注入，不重启）
    set_ignore_ssl,                    # 忽略 SSL 证书（CDP 协议）
    set_headless,                      # 有头/无头模式（如支持）
    set_viewport_size,                 # 窗口大小（page.set_viewport_size）
    inject_script,                     # 注入 JS 脚本（page.add_init_script）
]

JS_CONSOLE_TOOLS = [                   # JS 执行专属工具
    eval_js,                           # 执行 JS 代码
    eval_js_file,                      # 执行 JS 文件
]

# Skill（低频）工具——按需动态追加到任意节点的基础工具集
SKILL_TOOLS = {
    "overlay": dismiss_overlay,
}

# 根据节点类型选择专属工具集，再根据语义追加 Skill 工具
def select_tools_for_node(node_type: str, step_description: str) -> list:
    base = {
        "action": list(ACTION_TOOLS),
        "verify": list(VERIFY_TOOLS),
        "screenshot": list(SCREENSHOT_TOOLS),
        "browser_setting": list(BROWSER_SETTING_TOOLS),
        "js_console": list(JS_CONSOLE_TOOLS),
    }[node_type]

    # Skill 按需追加
    if needs_overlay_handling(step_description):
        base.append(SKILL_TOOLS["overlay"])
    return base
```
```

## 4. 技术选型

### 4.1 LangGraph Dynamic Tool Binding

LangGraph 原生支持按节点动态绑定工具：

```python
# 不是一次性给 agent 所有工具
agent = create_react_agent(model, tools=all_20_tools)

# 而是每个节点类型绑定自己的专属工具集
action_node = create_react_agent(model, tools=ACTION_TOOLS)
verify_node = create_react_agent(model, tools=VERIFY_TOOLS)
screenshot_node = create_react_agent(model, tools=SCREENSHOT_TOOLS)
config_node = create_react_agent(model, tools=BROWSER_SETTING_TOOLS)
js_node = create_react_agent(model, tools=JS_CONSOLE_TOOLS)
```

参考：
- [Stop Stuffing Your System Prompt: Build Scalable Agent Skills in LangGraph](https://pessini.medium.com/stop-stuffing-your-system-prompt-build-scalable-agent-skills-in-langgraph-a9856378e8f6)
- [LangGraph InjectedState](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/InjectedState)

### 4.2 InjectedState

LangGraph 的 `InjectedState` 注解可以把信息注入到工具执行中，但对 LLM 不可见：

```python
from langgraph.prebuilt import InjectedState

async def my_tool(state: Annotated[dict, InjectedState]) -> str:
    # state 中包含 analyze 的结果，但 LLM 看不到这个参数
    page_analysis = state["page_analysis"]
    ...
```

### 4.3 不选 MCP 的原因

MCP (Model Context Protocol) 是 Anthropic 的工具接入标准协议，但对我们来说太重了：

- 我们是自包含的浏览器测试框架，不需要跨进程工具发现
- LangGraph 的 Dynamic Tool Binding 已经满足我们的需求
- MCP 更适合需要接入外部服务（数据库、API）的场景

## 5. 影响范围

### 5.1 需要改动的模块

| 模块 | 改动 |
|------|------|
| `core/agent_loop.py` | 重构为多节点架构，每个节点绑定不同工具集 |
| `core/ai_context.py` | 添加节点类型感知，不同节点调用不同的 agent |
| `core/base_case.py` | step 执行流程适配节点化 |
| `core/flow.py` | flow API 适配节点化 |
| `core/yaml_runner.py` | YAML runner 适配节点化 |
| `core/tools.py` | 工具按类型分组导出 |

### 5.2 向后兼容

- 现有的 BaseCase、flow、YAML 写法应该保持不变
- 节点化是内部实现，用户侧 API 不变
- analyze 的自动触发逻辑需要保持：当 URL 变化时自动 re-analyze

## 6. 开放问题

1. **自动 Analyze 触发**：Action 节点是否需要自动检测 URL 变化并触发 Analyze？还是要求用户显式写 Analyze step？
2. **Skill 工具的语义匹配**：如何判断一个 step 描述需要加载 `dismiss_overlay`？（关键词匹配 vs LLM 判断 vs 用户标注）
3. **Replay 兼容**：节点化后，replay 脚本的生成和执行需要怎么调整？
4. **System Prompt 分离**：每个节点类型是否需要独立的 system prompt？

## 7. 参考资料

- [LangGraph Dynamic Tool Binding Discussion](https://www.reddit.com/r/LangChain/comments/1q8kgjp/langgraph_dynamic_tool_binding_with_skills/)
- [InjectedState | LangGraph Official Docs](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/InjectedState)
- [Stop Stuffing Your System Prompt (Medium)](https://pessini.medium.com/stop-stuffing-your-system-prompt-build-scalable-agent-skills-in-langgraph-a9856378e8f6)
- [ScaleMCP: Dynamic MCP Tools for LLM Agents](https://arxiv.org/html/2505.06416v1)
- [Tool Calling in LangChain, LangGraph, and MCP](https://dev.to/nikhil_ramank_152ca48266/-tool-calling-in-langchain-langgraph-and-mcp-three-layers-one-intelligent-system-4jf7)
