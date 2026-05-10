# Tools

Skiritai provides 16 tools that the AI agent uses during exploration. They're defined in `skiritai.core.tools` and `skiritai.core.perception`.

## Playwright Action Tools (14)

| Tool | Description |
|------|-------------|
| `navigate` | Navigate to a URL |
| `click` | Click an element by selector |
| `click_force` | Force-click (bypass visibility checks) |
| `fill` | Fill an input field |
| `type_text` | Type text character by character |
| `focus` | Focus an element |
| `scroll` | Scroll by coordinates |
| `hover` | Hover over an element |
| `select_option` | Select a `<select>` option |
| `eval_js` | Execute arbitrary JavaScript |
| `get_text` | Get text content of an element |
| `get_page_info` | Get current page title, URL, content |
| `wait_for` | Wait for element or timeout |
| `screenshot` | Take a page screenshot |

## DOM Perception Tools (2)

### `page_perceive`

Uses `browser-use`'s CDP-based DOM serialization to get structured page data, including all interactive elements and their CSS selectors.

### `find_element`

Natural-language element search with CJK-aware scoring. Accepts a description like "login button" or "搜索框" and returns the best-matching element.

## Tool Registration

Tools are registered via a decorator-based registry in `tool_registry.py`. New tools can be added by decorating a function with `@register_tool(name, description)`.
