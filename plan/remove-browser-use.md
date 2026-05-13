# 移除 browser-use 依赖 — 实施计划

## 目标

消除 `browser-use` 运行时依赖。用 Playwright 原生能力替代其 CDP DOM 序列化引擎
（DomService），对外公开 API（`page_perceive()`、`find_element()` 及感知层生命周期）
保持完全向后兼容。

## 动机

`browser-use` v0.12.6 是项目最大的依赖来源——引入了 260+ 个传递依赖（Google Cloud SDK、
PostHog、pyobjc、6 个 LLM SDK、文档处理库等），而项目实际仅使用其中的 2 个类
（BrowserSession、DomService）。

移除后 Python 包数量从 321 → ~60，磁盘占用从 425MB → ~80MB。

## 改动范围

| 文件 | 改动类型 | 预计行数 |
|---|---|---|
| `skiritai/core/perception.py` | **重写** — 用 Playwright JS evaluate 替代 browser_use | ~200 |
| `skiritai/core/base_case.py` | **简化** — 移除 CDP/BrowserSession 生命周期 | ~30 |
| `pyproject.toml` | **删除** — 移除 `"browser-use>=0.12.0"` | 1 行 |
| `uv.lock` | **自动** — 执行 `uv lock` 重新生成 | 自动 |

## 架构变更

### 改造前

```
用例启动
  → launch_browser_server() 打开 CDP 端口
  → create_browser_session(cdp_url) — browser-use BrowserSession 连接 CDP
  → 工具调用 DomService(cdp_url).get_serialized_dom_tree()
  → 返回 EnhancedDOMTreeNode 对象（含 .llm_representation()、.build_css_selector()）
用例结束
  → cleanup() 断开 BrowserSession
```

### 改造后

```
用例启动
  → launch_browser()（标准 Playwright，无需 CDP 端口）
  → 工具调用 page.evaluate(JS_DOM_SERIALIZER)
  → 返回普通 dict — Python 侧格式化 LLM 输出，JS 侧生成 CSS 选择器
用例结束
  → 无需清理（Playwright page 自行管理）
```

不再需要 CDP 端口，感知层在所有浏览器模式下统一工作。

---

## 分步实施

### 第一步 — 编写 JS DOM 序列化器（perception.py，约 80 行）

用注入 `page.evaluate()` 的 JS 函数替代 `DomService.get_serialized_dom_tree()`。
该 JS 需要：

1. 递归遍历 `document.body`
2. 筛选交互元素：`input`、`textarea`、`select`、`button`、`a[href]`、
   `[role="button"]`、`[role="link"]`、`[role="textbox"]`、`[role="combobox"]`、
   `[contenteditable="true"]`、`[tabindex]`
3. 对每个元素提取：
   - `tag_name`（如 "button"、"input"）
   - `attrs`：id、name、type、value、placeholder、aria-label、role、title、href、class
   - `text`：所有子节点文本（截取前 200 字符）
   - `css_selector`：构建唯一选择器（优先级：`#id` > `[name]` > tag + class + nth-child 路径）
4. 返回 JSON：`{ "elements": [...], "total_count": N, "url": "...", "title": "..." }`

当前 `tools.py` 的 `analyze_page()`（第 222-285 行）已做了一个简化版。我们实质上是
将其升级为输出结构化元素列表，而非分类桶。

### 第二步 — 重写 `_get_dom_state()`（perception.py，约 20 行）

替换当前 CDP 实现：

```python
# 改造前（第 74-85 行）
async def _get_dom_state() -> Any:
    from browser_use.dom.service import DomService
    session = get_browser_session()
    dom_service = DomService(browser_session=session)
    serialized_state, _enhanced_tree, _timing = await dom_service.get_serialized_dom_tree()
    return serialized_state
```

改为 Playwright 版本：

```python
# 改造后
async def _get_dom_state() -> dict:
    from skiritai.core.tools import get_page
    page = get_page()
    raw = await page.evaluate(JS_DOM_SERIALIZER)
    return _build_selector_map(raw)
```

`_build_selector_map()` 将 JS 返回的数组转换为 `{index: element_dict}` 字典，
保持与旧 `selector_map` 结构一致。

### 第三步 — 实现 `_llm_representation()`（perception.py，约 40 行）

旧版 `dom_state.llm_representation()`（来自 browser-use）输出格式如下：

```
[1] <button> "Submit" id="submit-btn" class="primary"
    [... CSS 选择器 ...]
```

这是纯字符串格式化。实现一个 Python 函数接收 dict 类型的 `selector_map`
并输出相同格式：

```python
def _llm_representation(selector_map: dict) -> str:
    lines = []
    for idx, el in sorted(selector_map.items()):
        lines.append(f'[{idx}] <{el["tag"]}> ...')
        lines.append(f'    {el["css_selector"]}')
    return "\n".join(lines)
```

### 第四步 — 适配 `find_element()`（perception.py，约 10 行改动）

当前 `find_element` 访问 `node.tag_name`、`node.get_all_children_text()`、
`node.attrs`、`node.build_css_selector()`——这些都是 `EnhancedDOMTreeNode` 的方法。

改造后变为普通 dict 键访问：

| 改造前（对象属性/方法） | 改造后（dict 键） |
|---|---|
| `node.tag_name` | `el["tag"]` |
| `node.get_all_children_text()` | `el["text"]` |
| `node.attrs.get("aria-label")` | `el["aria_label"]` 或 `el["attrs"]["aria-label"]` |
| `node.build_css_selector()` | `el["css_selector"]` |

评分逻辑（第 197-272 行）保持不变。

### 第五步 — 简化 `page_perceive()`（perception.py，约 5 行改动）

将 `dom_state.llm_representation()` 替换为新的 `_llm_representation(selector_map)`。
将 `dom_state.selector_map` 替换为 dict 类型的 selector_map。

### 第六步 — 清理 CDP/BrowserSession 层（perception.py + base_case.py）

从 `perception.py` 移除：
- `ContextVar _session_ctx`（第 25 行）
- `set_browser_session()`（第 28 行）
- `get_browser_session()`（第 33 行）
- `create_browser_session()`（第 44 行）
- `cleanup()`（第 61 行）

简化 `base_case.py`：
- 移除 `_init_perception()` 和 `_cleanup_perception()`
- 移除为感知层维护的 CDP 端口管理（Playwright 自身的 CDP 控制保留）
- 移除 `perception_mode` 状态追踪（不再需要——始终为 "playwright"）
- 移除 browser-use 导入的 try/except 守卫（第 374-383 行）

### 第七步 — 删除依赖声明

从 `pyproject.toml` 中删除一行：

```diff
- "browser-use>=0.12.0",
```

执行 `uv lock` 重新生成锁文件。预期减少约 260 个包。

---

## 关键设计决策

### 决策 1：JS DOM 序列化 vs CDP

**选择**：JS `page.evaluate()` 方案。

优势：
- 不依赖 browser-use 或任何 CDP 库
- 所有浏览器模式下均可工作（持久化、标准）
- Playwright 负责传输层，无需单独维护 WebSocket
- 项目中 `tools.py:analyze_page()` 已有此模式

劣势：
- JS 运行在页面上下文中（无法直接访问 Shadow DOM，需要额外处理）
- CSS 选择器质量相比 CDP 树遍历略有差异（不影响实际使用）

### 决策 2：selector_map 保持 dict[int, dict] 结构

**选择**：保留 `{index: element_dict}` 结构。

`selector_map` 仅在 `find_element()` 和 `page_perceive()` 中使用。两者只访问
少量明确定义的字段。使用普通 dict 比 `EnhancedDOMTreeNode` 对象更简洁。

### 决策 3：统一为单一路径

**选择**：移除 CDP "持久化模式"，统一为 Playwright 路径。

改造前存在两条路径：
- "browser_use" 模式：CDP DOM（更丰富，需持久化浏览器）
- "playwright_fallback" 模式：JS evaluate（更简单，始终可用）

改造后只有一条始终可用的路径。browser-use 的 DOM 输出在 JS 中复现。

---

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| JS 序列化器遗漏部分交互元素 | 低 | 中 | 覆盖全面的元素类型列表；已有 `analyze_page()` 覆盖常见场景 |
| CSS 选择器质量下降 | 低 | 低 | JS 中构建健壮选择器（id > name > class+nth-child）；Agent 也可使用文本点击 |
| `find_element` 评分行为变化 | 低 | 低 | 评分逻辑完整保留；仅数据访问方式变化 |
| 性能回退 | 极低 | 低 | JS evaluate 比 CDP 往返更快；元素数量有上限控制 |

## 回滚方案

若移除依赖后出现异常：
1. `git revert` 恢复 3 个改动文件
2. 重新添加 `"browser-use>=0.12.0"` 到 `pyproject.toml`
3. 执行 `uv lock`
4. 所有改动限定在 `perception.py` — 不影响其他模块

---

## 验证清单

- [ ] `uv run pytest` — 所有已有测试通过
- [ ] `uv run skiritai run examples/` — YAML 示例产出正确结果
- [ ] `page_perceive()` 输出格式与旧版 browser-use 一致
- [ ] `find_element()` 对 CJK 文本返回准确选择器
- [ ] `analyze_page()`（tools.py）继续作为降级方案工作
- [ ] `uv lock` 显示约 60 个包（从 321 下降）
- [ ] venv 磁盘占用从 ~425MB 降到 ~80MB
- [ ] CI 流水线（`test.yml`）通过
