# 工具

Skiritai 提供 16 个工具，供 AI Agent 在探索阶段使用。它们定义在 `skiritai.core.tools` 和 `skiritai.core.perception` 中。

## Playwright 操作工具（14 个）

| 工具              | 描述               |
|-----------------|------------------|
| `navigate`      | 导航到指定 URL        |
| `click`         | 通过选择器点击元素        |
| `click_force`   | 强制点击（绕过可见性检查）    |
| `fill`          | 填充输入框            |
| `type_text`     | 逐字符输入文本          |
| `focus`         | 聚焦元素             |
| `scroll`        | 按坐标滚动            |
| `hover`         | 悬停在元素上           |
| `select_option` | 选择 `<select>` 选项 |
| `eval_js`       | 执行任意 JavaScript  |
| `get_text`      | 获取元素文本内容         |
| `get_page_info` | 获取页面标题、URL、内容    |
| `wait_for`      | 等待元素出现或超时        |
| `screenshot`    | 截取页面截图           |

## DOM 感知工具（2 个）

### `page_perceive`

使用 `browser-use` 的 CDP DOM 序列化获取结构化页面数据，包含所有可交互元素及其 CSS 选择器。

### `find_element`

自然语言元素搜索，支持 CJK 感知评分。接受如 "login button" 或 "搜索框" 的描述，返回最佳匹配元素。

## 工具注册

工具通过 `tool_registry.py` 中基于装饰器的注册表进行管理。使用 `@register_tool(name, description)` 装饰函数即可添加新工具。
