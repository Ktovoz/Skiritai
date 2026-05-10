"""Playwright tools for LangGraph agent — text only, no vision."""
from __future__ import annotations

import contextvars
import tempfile
from pathlib import Path
from typing import Any

from skiritai.core.tool_registry import register_tool

_page_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("_page_ctx", default=None)


def set_page(page: Any):
    """Set the active Playwright page for tools to use."""
    _page_ctx.set(page)


def get_page() -> Any:
    """Get the active Playwright page."""
    page = _page_ctx.get()
    if page is None:
        raise RuntimeError("Page not initialized. Call set_page() first.")
    return page


@register_tool
async def navigate(url: str) -> str:
    """导航到指定 URL。

    Args:
        url: 目标 URL
    """
    page = get_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    return f"已导航到 {page.url}"


@register_tool
async def click(selector: str) -> str:
    """点击页面元素。使用 CSS 选择器定位元素。

    Args:
        selector: CSS 选择器，如 'button#submit', '.login-btn', 'text=登录'
    """
    page = get_page()
    await page.locator(selector).click()
    return f"已点击元素: {selector}"


@register_tool
async def click_text(text: str) -> str:
    """通过可见文本点击元素。不需要知道 CSS 选择器，直接根据页面上显示的文字来点击。

    适用场景：点击按钮、链接、菜单项等。会匹配包含该文本的第一个可见元素。

    Args:
        text: 页面上可见的文字内容，如 '登录'、'GCC Installation'
    """
    page = get_page()
    locator = page.get_by_text(text, exact=False).first
    await locator.click()
    return f"已点击文本为 '{text}' 的元素"


@register_tool
async def click_force(selector: str) -> str:
    """强制点击元素（即使元素不可见）。适用于被遮挡或隐藏的元素。

    Args:
        selector: CSS 选择器
    """
    page = get_page()
    await page.locator(selector).click(force=True)
    return f"已强制点击元素: {selector}"


@register_tool
async def fill(selector: str, text: str) -> str:
    """在输入框中填写文本。要求元素可见。

    Args:
        selector: 输入框的 CSS 选择器
        text: 要填写的文本内容
    """
    page = get_page()
    await page.locator(selector).fill(text)
    return f"已在 {selector} 中填写: {text}"


@register_tool
async def type_text(selector: str, text: str) -> str:
    """逐字符输入文本到元素。适用于隐藏或动态显示的输入框。

    Args:
        selector: 输入框的 CSS 选择器
        text: 要输入的文本内容
    """
    page = get_page()
    await page.locator(selector).press_sequentially(text)
    return f"已在 {selector} 中输入: {text}"


@register_tool
async def focus(selector: str) -> str:
    """聚焦到指定元素。

    Args:
        selector: 元素的 CSS 选择器
    """
    page = get_page()
    await page.locator(selector).focus()
    return f"已聚焦到 {selector}"


@register_tool
async def get_text(selector: str) -> str:
    """获取指定元素的文本内容。

    Args:
        selector: 元素的 CSS 选择器
    """
    page = get_page()
    text = await page.locator(selector).text_content()
    return f"元素文本: {text}"


@register_tool
async def wait_for(selector: str, timeout: int = 5000) -> str:
    """等待指定元素出现。

    Args:
        selector: 等待出现的元素 CSS 选择器
        timeout: 超时时间（毫秒），默认 5000
    """
    page = get_page()
    await page.locator(selector).wait_for(timeout=timeout)
    return f"元素已出现: {selector}"


@register_tool
async def scroll(direction: str, amount: int = 500) -> str:
    """滚动页面。

    Args:
        direction: 滚动方向，'up' 或 'down'
        amount: 滚动像素数，默认 500
    """
    page = get_page()
    y = amount if direction == "down" else -amount
    await page.mouse.wheel(0, y)
    return f"已向{direction}滚动 {amount}px"


@register_tool
async def get_page_info() -> str:
    """获取当前页面的标题、URL 和页面文本摘要。"""
    page = get_page()
    title = await page.title()
    url = page.url
    body_text = await page.evaluate("document.body?.innerText?.substring(0, 2000) || ''")
    return f"标题: {title}\nURL: {url}\n页面文本:\n{body_text}"


@register_tool
async def eval_js(expression: str) -> str:
    """在页面中执行 JavaScript 表达式并返回结果。

    Args:
        expression: 要执行的 JS 表达式
    """
    page = get_page()
    result = await page.evaluate(expression)
    return f"JS 执行结果: {result}"


@register_tool
async def select_option(selector: str, value: str) -> str:
    """在下拉选择框中选择选项。

    Args:
        selector: select 元素的 CSS 选择器
        value: 要选择的选项值
    """
    page = get_page()
    await page.locator(selector).select_option(value)
    return f"已选择 {value} in {selector}"


@register_tool
async def hover(selector: str) -> str:
    """鼠标悬停在元素上。

    Args:
        selector: 元素的 CSS 选择器
    """
    page = get_page()
    await page.locator(selector).hover()
    return f"已悬停在 {selector}"


@register_tool
async def analyze_page() -> str:
    """分析当前页面的 DOM 结构，返回所有可交互元素的详细信息。

    当 AI 无法找到目标元素时，必须使用此工具获取页面的真实 DOM 结构，
    而不是依赖训练数据中已知的选择器（选择器可能在页面更新后已失效）。

    返回值是 JSON 格式，包含：
    - inputs: 所有可见输入框（tag, type, name, id, placeholder, selector）
    - buttons: 所有可见按钮（text, id, selector）
    - links: 可见链接（text, href），最多 20 条
    """
    page = get_page()
    return await page.evaluate("""
        (() => {
            const isVisible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' &&
                       style.visibility !== 'hidden' &&
                       style.opacity !== '0' &&
                       rect.width > 0 && rect.height > 0;
            };
            const mkSelector = (el) => {
                if (el.id) return '#' + CSS.escape(el.id);
                if (el.name) return '[name="' + el.name + '"]';
                if (el.className && typeof el.className === 'string') {
                    const cls = el.className.trim().split(/\\s+/)[0];
                    if (cls) return el.tagName.toLowerCase() + '.' + CSS.escape(cls);
                }
                return el.tagName.toLowerCase();
            };
            const inputs = [...document.querySelectorAll('input, textarea, select')]
                .filter(isVisible)
                .slice(0, 30)
                .map(el => ({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    name: el.name || '',
                    id: el.id || '',
                    placeholder: (el.placeholder || '').substring(0, 60),
                    selector: mkSelector(el)
                }));
            const buttons = [...document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]')]
                .filter(isVisible)
                .slice(0, 20)
                .map(el => {
                    const hasSvg = el.querySelector('svg') !== null;
                    const hasIcon = el.className && /icon|search|menu|close|hamburger/i.test(el.className);
                    return {
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || el.value || '').trim().substring(0, 60),
                        id: el.id || '',
                        aria_label: (el.getAttribute('aria-label') || '').substring(0, 80),
                        title: (el.getAttribute('title') || '').substring(0, 80),
                        classes: (typeof el.className === 'string' ? el.className.trim() : '').substring(0, 100),
                        has_svg: hasSvg,
                        selector: mkSelector(el)
                    };
                });
            const links = [...document.querySelectorAll('a[href]')]
                .filter(isVisible)
                .slice(0, 20)
                .map(el => ({
                    text: (el.textContent || '').trim().substring(0, 60),
                    href: el.href
                }));
            return JSON.stringify({
                url: location.href,
                title: document.title,
                inputs,
                buttons,
                links,
                counts: {inputs: inputs.length, buttons: buttons.length, links: links.length}
            }, null, 2);
        })()
    """)


@register_tool
async def screenshot(name: str = "screenshot") -> str:
    """截取当前页面的截图并保存。

    Args:
        name: 截图文件名（不含扩展名），默认 'screenshot'
    """
    page = get_page()
    path = str(Path(tempfile.gettempdir()) / f"testagent_{name}.png")
    await page.screenshot(path=path, full_page=True)
    return f"截图已保存到 {path}"
