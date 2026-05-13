"""DOM perception layer — Playwright-native JS DOM serialization.

Provides read-only tools that analyze the current page via Playwright's
``page.evaluate()``, injecting a JavaScript serializer that walks the DOM
tree and returns structured interactive-element data.

No external dependencies beyond Playwright — previously used browser-use's
CDP-based DomService, now replaced by pure JS + Playwright.

The public API (``page_perceive``, ``find_element``) is unchanged.
"""
from __future__ import annotations

from skiritai.core.tool_registry import register_tool
from skiritai.logger import logger

# ---------------------------------------------------------------------------
# JS DOM Serializer — injected via page.evaluate()
# ---------------------------------------------------------------------------

_JS_DOM_SERIALIZER = r"""
(() => {
    const INTERACTIVE_TAGS = new Set([
        'input', 'textarea', 'select', 'button', 'a'
    ]);
    const INTERACTIVE_ROLES = new Set([
        'button', 'link', 'textbox', 'combobox', 'listbox',
        'menuitem', 'option', 'tab', 'checkbox', 'radio',
        'switch', 'slider', 'spinbutton', 'searchbox'
    ]);

    const isVisible = (el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.display !== 'none' &&
               style.visibility !== 'hidden' &&
               style.opacity !== '0' &&
               rect.width > 0 && rect.height > 0;
    };

    const isInteractive = (el) => {
        const tag = el.tagName.toLowerCase();
        if (INTERACTIVE_TAGS.has(tag)) {
            // Skip hidden inputs and non-interactive types
            if (tag === 'input') {
                const type = (el.type || 'text').toLowerCase();
                if (type === 'hidden') return false;
            }
            if (tag === 'a' && !el.href) return false;
            return true;
        }
        if (el.hasAttribute('contenteditable') && el.getAttribute('contenteditable') !== 'false') {
            return true;
        }
        if (el.hasAttribute('tabindex')) return true;
        const role = (el.getAttribute('role') || '').toLowerCase();
        if (INTERACTIVE_ROLES.has(role)) return true;
        // onclick handlers
        if (typeof el.onclick === 'function') return true;
        return false;
    };

    const buildSelector = (el) => {
        if (el.id) return '#' + CSS.escape(el.id);
        const tag = el.tagName.toLowerCase();
        if (el.name) return tag + '[name="' + el.name.replace(/"/g, '\\"') + '"]';
        // Build a path with :nth-child for uniqueness
        const parts = [];
        let current = el;
        while (current && current !== document.body && current !== document.documentElement) {
            const parent = current.parentElement;
            if (!parent) break;
            const idx = [...parent.children].indexOf(current) + 1;
            let seg = current.tagName.toLowerCase();
            if (current.id) {
                parts.unshift('#' + CSS.escape(current.id));
                break;
            }
            if (current.className && typeof current.className === 'string') {
                const cls = current.className.trim().split(/\s+/)[0];
                if (cls && !cls.match(/^[0-9]/)) {
                    seg += '.' + CSS.escape(cls);
                }
            }
            if (parent.children.length > 1) {
                seg += ':nth-child(' + idx + ')';
            }
            parts.unshift(seg);
            current = parent;
        }
        return parts.join(' > ') || tag;
    };

    const MAX_ELEMENTS = 100;
    const MAX_DEPTH = 50;

    const getText = (el) => {
        if (el.tagName.toLowerCase() === 'input') return el.value || '';
        return (el.textContent || '').trim().substring(0, 200);
    };

    const walk = (root, elements, depth) => {
        if (!root || root.nodeType !== 1) return;
        if (depth > MAX_DEPTH) return;
        if (!isVisible(root)) return;
        if (elements.length >= MAX_ELEMENTS) return;
        if (isInteractive(root)) {
            const tag = root.tagName.toLowerCase();
            const text = getText(root);
            elements.push({
                tag: tag,
                text: text,
                id: root.id || '',
                name: root.getAttribute('name') || '',
                type: root.getAttribute('type') || '',
                value: root.value || '',
                placeholder: root.getAttribute('placeholder') || '',
                aria_label: root.getAttribute('aria-label') || '',
                role: root.getAttribute('role') || '',
                title: root.getAttribute('title') || '',
                href: root.href || root.getAttribute('href') || '',
                class: (typeof root.className === 'string' ? root.className : ''),
                selector: buildSelector(root)
            });
        }
        // Only recurse if element has children — skip text/comment nodes
        if (root.children && elements.length < MAX_ELEMENTS) {
            for (const child of root.children) {
                walk(child, elements, depth + 1);
            }
        }
    };

    const elements = [];
    walk(document.body, elements, 0);

    return JSON.stringify({
        url: location.href,
        title: document.title,
        total_count: elements.length,
        elements: elements
    });
})()
"""

# ---------------------------------------------------------------------------
# Python helpers — convert JS output to selector_map + LLM representation
# ---------------------------------------------------------------------------


def _build_selector_map(raw_json: str) -> dict[int, dict]:
    """Parse the JS serializer output into a {index: element_dict} map.

    The index is 1-based, matching the old browser-use selector_map convention
    so that ``find_element`` scoring and ``page_perceive`` output remain identical.
    """
    import json
    data = json.loads(raw_json)
    elements = data.get("elements", [])
    smap: dict[int, dict] = {}
    for i, el in enumerate(elements):
        smap[i + 1] = {
            "tag": el.get("tag", ""),
            "text": el.get("text", ""),
            "id": el.get("id", ""),
            "name": el.get("name", ""),
            "type": el.get("type", ""),
            "value": el.get("value", ""),
            "placeholder": el.get("placeholder", ""),
            "aria_label": el.get("aria_label", ""),
            "role": el.get("role", ""),
            "title": el.get("title", ""),
            "href": el.get("href", ""),
            "class": el.get("class", ""),
            "selector": el.get("selector", ""),
        }
    return smap


def _llm_representation(selector_map: dict[int, dict]) -> str:
    """Format the selector_map as LLM-readable text.

    Output format (matches old browser-use ``llm_representation()``):

        [1] <button> "Submit" id="submit-btn"
            #submit-btn
        [2] <input> type="text" placeholder="搜索"
            input[name="q"]

    """
    lines: list[str] = []
    for idx in sorted(selector_map.keys()):
        el = selector_map[idx]
        tag = el["tag"]
        parts = [f"[{idx}] <{tag}>"]

        # Descriptive attributes
        label_parts = []
        text = el["text"]
        if text:
            label_parts.append(f'"{text}"')
        for attr, label in [
            ("id", "id"), ("name", "name"), ("type", "type"),
            ("placeholder", "placeholder"), ("role", "role"),
            ("aria_label", "aria-label"), ("title", "title"),
        ]:
            val = el.get(attr, "")
            if val:
                label_parts.append(f'{label}="{val}"')
        if label_parts:
            parts.append(" " + " ".join(label_parts))

        lines.append("".join(parts))
        lines.append(f"    {el['selector']}")

    return "\n".join(lines)


def _extract_cjk_tokens(text: str) -> list[str]:
    """Extract individual CJK characters and bigrams from text.

    This enables matching Chinese descriptions like "搜索按钮" against
    element text, even though Chinese doesn't use spaces as word boundaries.

    Returns tokens in order: bigrams first (higher quality), then single chars.
    """

    # Extract only CJK characters (preserving order)
    cjk_chars = []
    for ch in text:
        cp = ord(ch)
        if (
                (0x4E00 <= cp <= 0x9FFF)  # CJK Unified Ideographs
                or (0x3400 <= cp <= 0x4DBF)  # CJK Extension A
                or (0x3000 <= cp <= 0x303F)  # CJK Symbols and Punctuation
                or (0xF900 <= cp <= 0xFAFF)  # CJK Compatibility Ideographs
                or (0xFF00 <= cp <= 0xFFEF)  # Halfwidth and Fullwidth Forms
        ):
            cjk_chars.append(ch)

    if len(cjk_chars) < 2:
        return cjk_chars

    tokens = []
    # Add bigrams (pairs of adjacent CJK characters) — these are high-quality matches
    for i in range(len(cjk_chars) - 1):
        tokens.append(cjk_chars[i] + cjk_chars[i + 1])
    # Add individual characters as fallback
    tokens.extend(cjk_chars)

    return tokens


# ---------------------------------------------------------------------------
# Perception tools (read-only, never modify the page)
# ---------------------------------------------------------------------------

async def _get_dom_state() -> dict[int, dict]:
    """Get the current page's interactive elements as a selector_map.

    Injects a JS serializer via Playwright ``page.evaluate()``, then converts
    the JSON output into a ``{index: element_dict}`` map compatible with the
    old browser-use API.

    Returns:
        dict[int, dict] — 1-indexed selector_map
    """
    from skiritai.core.tools import get_page
    page = get_page()
    raw = await page.evaluate(_JS_DOM_SERIALIZER)
    return _build_selector_map(raw)


@register_tool
async def page_perceive() -> str:
    """深度分析当前页面的 DOM 结构，返回所有可交互元素的结构化信息。

    这是一个只读感知工具，使用 Playwright JS evaluate 分析页面。
    返回元素的索引号、选择器、文本、角色等信息。
    在执行操作前调用此工具可以帮助你准确定位元素。

    Returns:
        页面结构化 DOM 信息
    """
    try:
        selector_map = await _get_dom_state()
    except Exception as e:
        logger.warning(f"[Perception] page_perceive failed: {e}")
        return f"DOM 分析失败: {e}"

    interactive_count = len(selector_map)

    header = (
        f"可交互元素数量: {interactive_count}\n"
        f"---\n"
    )

    llm_text = _llm_representation(selector_map)
    output = header + llm_text

    # Truncate at last complete line to avoid cutting mid-element
    if len(output) > 6000:
        cut = output[:6000]
        last_nl = cut.rfind("\n")
        if last_nl > 0:
            cut = cut[:last_nl]
        output = cut + "\n... (截断，使用 find_element 获取更多细节)"

    return output


@register_tool
async def find_element(description: str) -> str:
    """用自然语言描述查找页面元素，返回最佳匹配的 CSS 选择器。

    这是一个只读感知工具。使用 Playwright JS evaluate 获取页面元素，
    然后根据描述匹配最合适的元素。返回选择器供 click/fill 等操作工具使用。

    Args:
        description: 对目标元素的描述，如 "搜索按钮"、"用户名输入框"、"提交"
    """
    try:
        selector_map = await _get_dom_state()
    except Exception as e:
        logger.warning(f"[Perception] find_element failed: {e}")
        return f"DOM 分析失败: {e}"

    desc = description.lower()

    if not selector_map:
        return "页面上没有找到可交互元素。"

    # Score each interactive element against the description
    candidates = []

    # Tokenize description for matching:
    # - Split on whitespace for English-style tokens
    # - Also extract individual CJK characters and bigrams for Chinese text
    keywords = desc.split()
    cjk_tokens = _extract_cjk_tokens(desc)
    all_tokens = keywords + [t for t in cjk_tokens if t not in keywords]

    for idx, el in selector_map.items():
        score = 0

        tag = el.get("tag", "")
        text = el.get("text", "")
        aria_label = el.get("aria_label", "")
        placeholder = el.get("placeholder", "")
        title_attr = el.get("title", "")
        name_attr = el.get("name", "")
        role = el.get("role", "")
        node_id = el.get("id", "")
        input_type = el.get("type", "")
        value = el.get("value", "")
        css_selector = el.get("selector", "")

        all_text = ' '.join(filter(None, [
            text, aria_label, placeholder, title_attr, name_attr,
            node_id, value, tag, role, input_type
        ])).lower()

        # Exact substring match on the full description
        if desc in all_text:
            score += 10

        # Keyword match (whitespace-split words)
        for kw in keywords:
            if len(kw) < 2:
                continue
            if kw in all_text:
                score += 3

        # CJK character/bigram match (for Chinese text like "搜索按钮")
        for token in cjk_tokens:
            if len(token) >= 2 and token in all_text:
                score += 4  # bigram match is stronger than single-char
            elif len(token) == 1 and token in all_text:
                score += 1  # single char match is weaker

        # Field-specific boosts
        for field in [aria_label, placeholder, title_attr, name_attr, node_id]:
            if field and desc in field.lower():
                score += 5

        if role and desc in role.lower():
            score += 3
        if input_type and desc in input_type.lower():
            score += 3
        if tag and desc in tag.lower():
            score += 1

        if score > 0:
            candidates.append({
                'index': idx,
                'selector': css_selector,
                'tag': tag,
                'score': score,
                'text': text[:80],
                'aria_label': aria_label,
                'placeholder': placeholder,
                'role': role,
                'type': input_type,
                'id': node_id,
                'name': name_attr,
            })

    if not candidates:
        return (
            f"未找到匹配 \"{description}\" 的元素。\n"
            f"建议用 page_perceive 查看页面上所有可交互元素。"
        )

    # Sort by score descending
    candidates.sort(key=lambda c: c['score'], reverse=True)

    lines = [f"搜索: \"{description}\"", f"匹配数量: {len(candidates)}", ""]

    for i, c in enumerate(candidates[:5]):
        rank = "【最佳匹配】" if i == 0 else f"  候选 {i + 1}"
        lines.append(f"{rank} 选择器: {c['selector']}")
        parts = [f"<{c['tag']}>"]
        for key, label in [
            ('type', 'type'), ('role', 'role'), ('id', 'id'),
            ('name', 'name'), ('aria_label', 'aria-label'),
            ('placeholder', 'placeholder'),
        ]:
            if c.get(key):
                parts.append(f'{label}="{c[key]}"')
        if c.get('text'):
            parts.append(f'text="{c["text"]}"')
        lines.append(f"    {' '.join(parts)} (score={c['score']})")

    return "\n".join(lines)
