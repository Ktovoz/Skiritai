# 感知层

Skiritai 的感知层通过 [browser-use](https://github.com/browser-use/browser-use) 的 CDP DOM 序列化引擎，为 AI Agent
提供结构化的页面理解。

## 概述

不依赖 Playwright 的 `page.evaluate()` 进行 DOM 遍历，感知层使用 Chrome DevTools Protocol (CDP)
将整个页面序列化为结构化的可交互元素树——每个元素都带有 CSS 选择器、文本、角色和属性等注释。

## 架构

```
Python 进程
┌─────────────────────────────────┐
│  Playwright (CDP 客户端 #1)    │
│    └─ Playwright 操作           │
│                                  │
│  browser-use (CDP 客户端 #2)    │
│    └─ DomService ── DOM 树      │
│       ├─ selector_map             │
│       └─ llm_representation()     │
└─────────────────────────────────┘
         │             │
    CDP  │    ws://    │  CDP
         │             │
    ┌────┴─────────────┴────┐
    │    Chromium (CDP)     │
    │  remote-debugging-port│
    └───────────────────────┘
```

Chrome 支持**多个并发的 CDP 客户端**——Playwright 和 browser-use 通过同一端口独立运行。

## 感知模式

感知层的可用性取决于浏览器模式：

| 浏览器模式    | 感知方式                   | 回退方案                |
|----------|------------------------|---------------------|
| 持久化（CDP） | browser-use DomService | Playwright evaluate |
| 标准       | 不可用                    | Playwright evaluate |

通过 `self.ctx.perception_mode` 访问：

```python
# 在任意步骤方法中：
if self.ctx.perception_mode == "browser_use":
    print("完整 DOM 感知可用")
else:
    print("Playwright evaluate 回退方案（无 CDP 访问）")
```

## 感知工具

### `page_perceive`

深度 DOM 分析，返回所有可交互元素的结构化元数据：

```
可交互元素数量: 47
---
[1] <button> "Submit" id="submit-btn" class="primary"
    [... 带 CSS 选择器的选择器映射 ...]
[2] <input> type="text" name="username" placeholder="Enter username"
    [...]
```

输出截断为 6000 字符以适应 LLM 上下文窗口。需要针对性搜索时使用 `find_element`。

### `find_element`

自然语言元素搜索，支持专门的 CJK 评分：

```
搜索: "搜索框"
匹配数量: 3

【最佳匹配】 选择器: #main-search input[type="text"]
    <input> type="text" placeholder="搜索" (score=18)
   候选 2 选择器: #sidebar-search
    <input> type="text" (score=7)
   候选 3 选择器: .search-icon
    <button> aria-label="搜索" (score=5)
```

## CJK 感知匹配

`find_element` 使用专门的评分算法处理中文、日文和韩文文本：

1. **二元组提取** — 相邻的 CJK 字符组成二元组（如"搜索"、"按钮"），以复合分词匹配
2. **Unicode 范围检测** — 识别 CJK 统一表意文字、扩展 A 区、符号区、兼容表意文字区和全角/半角形式区
3. **加权评分**：
    - 精确子串匹配：+10
    - CJK 二元组匹配：+4（更高质量）
    - 单个 CJK 字符匹配：+1（较低质量，回退方案）
    - 空格分隔关键词匹配：+3
    - aria-label/placeholder/name/id 匹配：+5
    - role/type 匹配：+3

## AI 工作流中的感知

AI Agent 的默认系统提示词引导其使用感知工具：

1. **进入页面** → 调用 `page_perceive` 了解可用元素
2. **查找目标** → 使用 `find_element("描述")` 进行自然语言搜索
3. **执行操作** → 使用返回的 CSS 选择器调用 click/fill/navigate
4. **验证结果** → 再次调用 `page_perceive` 确认

## 生命周期

```
用例开始
  → BaseCase 启动浏览器（Playwright）并开启 CDP 端口
  → set_browser_session(cdp_url) 将 browser-use 连接到同一端口
  → 工具（page_perceive、find_element）使用 DomService
用例结束
  → cleanup() 断开 browser-use 会话
```
