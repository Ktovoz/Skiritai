# Perception Layer

Skiritai's perception layer gives the AI agent structured page understanding via [browser-use](https://github.com/browser-use/browser-use)'s CDP-based DOM serialization engine.

## Overview

Instead of relying on Playwright's `page.evaluate()` for DOM traversal, the perception layer uses Chrome DevTools Protocol (CDP) to serialize the full page into a structured tree of interactive elements — each annotated with CSS selectors, text, roles, and attributes.

## Architecture

```
Python Process
┌─────────────────────────────────┐
│  Playwright (CDP client #1)      │
│    └─ Playwright actions         │
│                                  │
│  browser-use (CDP client #2)     │
│    └─ DomService ── DOM tree     │
│       ├─ selector_map             │
│       └─ llm_representation()    │
└─────────────────────────────────┘
         │             │
    CDP  │    ws://    │  CDP
         │             │
    ┌────┴─────────────┴────┐
    │    Chromium (CDP)     │
    │  remote-debugging-port│
    └───────────────────────┘
```

Chrome supports **multiple concurrent CDP clients** — Playwright and browser-use operate independently over the same port.

## Perception Mode

The perception layer availability depends on the browser mode:

| Browser Mode | Perception | Fallback |
|-------------|------------|----------|
| Persistent (CDP) | browser-use DomService | Playwright evaluate |
| Standard | Not available | Playwright evaluate |

Access via `self.ctx.perception_mode`:

```python
# In any step method:
if self.ctx.perception_mode == "browser_use":
    print("Full DOM perception available")
else:
    print("Playwright evaluate fallback (no CDP access)")
```

## Perception Tools

### `page_perceive`

Deep DOM analysis returning all interactive elements with structured metadata:

```
可交互元素数量: 47
---
[1] <button> "Submit" id="submit-btn" class="primary"
    [... selector map with CSS selectors ...]
[2] <input> type="text" name="username" placeholder="Enter username"
    [...]
```

The output is truncated at 6000 characters to fit LLM context windows. Use `find_element` for targeted searches.

### `find_element`

Natural-language element search with specialized CJK scoring:

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

## CJK-Aware Matching

`find_element` uses a specialized scoring algorithm for Chinese, Japanese, and Korean text:

1. **Bigram extraction** — Adjacent CJK characters form bigrams (e.g., "搜索", "按钮") that are matched as compound tokens
2. **Unicode range detection** — Identifies CJK Unified Ideographs, Extension A, Symbols, Compatibility Ideographs, and Fullwidth Forms
3. **Weighted scoring**:
   - Exact substring match: +10
   - CJK bigram match: +4 (higher quality)
   - Single CJK char match: +1 (lower quality, fallback)
   - Whitespace-split keyword match: +3
   - Match in aria-label/placeholder/name/id: +5
   - Match in role/type: +3

## Perception in AI Workflows

The AI agent's default system prompt guides it to use perception tools:

1. **Enter page** → Call `page_perceive` to understand available elements
2. **Find target** → Use `find_element("描述")` for natural language search
3. **Execute action** → Use returned CSS selectors with click/fill/navigate
4. **Verify result** → Call `page_perceive` again to confirm

## Lifecycle

```
Case starts
  → BaseCase launches browser (Playwright) with CDP port
  → set_browser_session(cdp_url) connects browser-use to same port
  → Tools (page_perceive, find_element) use DomService
Case ends
  → cleanup() disconnects browser-use session
```
