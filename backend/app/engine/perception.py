"""DOM perception layer — reuses browser-use DomService for structured page understanding.

Provides read-only tools that analyze the current page via browser-use's CDP-based
DOM extraction.  A single BrowserSession is created per case and shared across all
perception calls, connecting to the same CDP port as Playwright.

Lifecycle:
    1. Case starts → BaseCase launches browser (Playwright) with CDP port
    2. set_browser_session(cdp_url) connects browser-use BrowserSession to same port
    3. Tools (page_perceive, find_element) call DomService for read-only analysis
    4. Case ends → cleanup() disconnects browser-use session

No dual-session conflicts: both Playwright and browser-use share the same CDP port
via independent WebSocket connections (Chrome supports multiple CDP clients).
"""
from __future__ import annotations

import json
from typing import Any

import contextvars

from app.engine.tool_registry import register_tool
from app.logger import logger

# ContextVar holding the active browser-use BrowserSession (set once per case)
_session_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("_bu_session", default=None)


def set_browser_session(session: Any) -> None:
    """Set the active browser-use BrowserSession for perception tools."""
    _session_ctx.set(session)


def get_browser_session() -> Any:
    """Get the active browser-use BrowserSession."""
    session = _session_ctx.get()
    if session is None:
        raise RuntimeError(
            "browser-use BrowserSession not initialized. "
            "Call set_browser_session() first."
        )
    return session


async def create_browser_session(cdp_url: str) -> Any:
    """Create and connect a browser-use BrowserSession to an existing CDP endpoint.

    Args:
        cdp_url: CDP HTTP URL like "http://127.0.0.1:9222"

    Returns:
        Connected BrowserSession instance
    """
    from browser_use.browser.session import BrowserSession

    session = BrowserSession(cdp_url=cdp_url)
    await session.connect()
    logger.info(f"[Perception] browser-use BrowserSession connected to {cdp_url}")
    return session


async def cleanup() -> None:
    """Disconnect the browser-use BrowserSession (does NOT close the browser)."""
    session = _session_ctx.get()
    if session is not None:
        try:
            await session.stop()
            logger.info("[Perception] browser-use BrowserSession stopped")
        except Exception as e:
            logger.debug(f"[Perception] Error stopping session: {e}")
        finally:
            _session_ctx.set(None)


async def _get_dom_state() -> Any:
    """Get the current page's serialized DOM state via browser-use DomService.

    Returns:
        SerializedDOMState with selector_map and llm_representation()
    """
    from browser_use.dom.service import DomService

    session = get_browser_session()
    dom_service = DomService(browser_session=session)
    serialized_state, _enhanced_tree, _timing = await dom_service.get_serialized_dom_tree()
    return serialized_state


def _extract_cjk_tokens(text: str) -> list[str]:
    """Extract individual CJK characters and bigrams from text.

    This enables matching Chinese descriptions like "搜索按钮" against
    element text, even though Chinese doesn't use spaces as word boundaries.

    Returns tokens in order: bigrams first (higher quality), then single chars.
    """
    import unicodedata

    # Extract only CJK characters (preserving order)
    cjk_chars = []
    for ch in text:
        cp = ord(ch)
        if (
            (0x4E00 <= cp <= 0x9FFF)      # CJK Unified Ideographs
            or (0x3400 <= cp <= 0x4DBF)    # CJK Extension A
            or (0x3000 <= cp <= 0x303F)    # CJK Symbols and Punctuation
            or (0xF900 <= cp <= 0xFAFF)    # CJK Compatibility Ideographs
            or (0xFF00 <= cp <= 0xFFEF)    # Halfwidth and Fullwidth Forms
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

@register_tool
async def page_perceive() -> str:
    """深度分析当前页面的 DOM 结构，返回所有可交互元素的结构化信息。

    这是一个只读感知工具，使用 browser-use 的 DOM 引擎分析页面。
    返回元素的索引号、选择器、文本、角色等信息。
    在执行操作前调用此工具可以帮助你准确定位元素。

    Returns:
        页面结构化 DOM 信息（browser-use DomService 输出）
    """
    try:
        dom_state = await _get_dom_state()
    except Exception as e:
        logger.warning(f"[Perception] page_perceive failed: {e}")
        return f"DOM 分析失败: {e}"

    # Use browser-use's built-in LLM representation
    llm_text = dom_state.llm_representation()

    # Add summary header
    selector_map = dom_state.selector_map
    interactive_count = len(selector_map)

    header = (
        f"可交互元素数量: {interactive_count}\n"
        f"---\n"
    )

    output = header + llm_text

    # Truncate if too long for LLM context
    if len(output) > 6000:
        output = output[:6000] + "\n... (截断，使用 find_element 获取更多细节)"

    return output


@register_tool
async def find_element(description: str) -> str:
    """用自然语言描述查找页面元素，返回最佳匹配的 CSS 选择器。

    这是一个只读感知工具。使用 browser-use 的 DOM 引擎获取页面元素，
    然后根据描述匹配最合适的元素。返回选择器供 click/fill 等操作工具使用。

    Args:
        description: 对目标元素的描述，如 "搜索按钮"、"用户名输入框"、"提交"
    """
    try:
        dom_state = await _get_dom_state()
    except Exception as e:
        logger.warning(f"[Perception] find_element failed: {e}")
        return f"DOM 分析失败: {e}"

    selector_map = dom_state.selector_map
    desc = description.lower()

    if not selector_map:
        return f"页面上没有找到可交互元素。"

    # Score each interactive element against the description
    candidates = []

    # Tokenize description for matching:
    # - Split on whitespace for English-style tokens
    # - Also extract individual CJK characters and bigrams for Chinese text
    keywords = desc.split()
    cjk_tokens = _extract_cjk_tokens(desc)
    all_tokens = keywords + [t for t in cjk_tokens if t not in keywords]

    for idx, node in selector_map.items():
        score = 0
        # Collect text fields from the node
        text_fields = []

        # node is EnhancedDOMTreeNode — access its attributes
        tag = getattr(node, 'tag_name', '') or ''
        text = ''
        try:
            text = node.get_all_children_text() or ''
        except Exception:
            pass
        aria_label = getattr(node, 'attrs', {}).get('aria-label', '') or ''
        placeholder = getattr(node, 'attrs', {}).get('placeholder', '') or ''
        title_attr = getattr(node, 'attrs', {}).get('title', '') or ''
        name_attr = getattr(node, 'attrs', {}).get('name', '') or ''
        role = getattr(node, 'attrs', {}).get('role', '') or ''
        node_id = getattr(node, 'attrs', {}).get('id', '') or ''
        input_type = getattr(node, 'attrs', {}).get('type', '') or ''
        value = getattr(node, 'attrs', {}).get('value', '') or ''
        href = getattr(node, 'attrs', {}).get('href', '') or ''
        css_selector = ''
        try:
            css_selector = node.build_css_selector()
        except Exception:
            pass

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
