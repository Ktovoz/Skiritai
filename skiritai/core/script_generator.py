"""Replay script generator — converts agent tool-call history into standalone Python scripts."""
from __future__ import annotations

from skiritai.core.agent_loop import PERCEPTION_TOOLS
from skiritai.logger import logger

# Read-only tools that should never appear in replay scripts
_READONLY_TOOLS = PERCEPTION_TOOLS | {"get_page_info", "get_text", "response"}


def generate_replay_script(step_id: str, agent_steps: list[dict]) -> str:
    """Generate a standalone replay script from agent's tool-calling history.

    The generated script:
    - Can be run independently: python <script>.py
    - Can be imported and run via: await run(page, context)
    - Filters out perception / read-only tools
    - Includes proper imports and a __main__ block
    - Escapes special characters in arguments
    """
    # Filter out read-only steps
    action_steps = [
        s for s in agent_steps
        if s.get("action") not in _READONLY_TOOLS
    ]

    action_lines = []
    for step in action_steps:
        action = step.get("action", "")
        args = step.get("args", {})
        line = _action_to_line(action, args)
        if line:
            action_lines.append(line)
        elif action not in _READONLY_TOOLS:
            logger.warning(
                f"[ScriptGen] Unrecognized action '{action}' — no replay line generated. "
                f"Add a handler in _action_to_line or consider adding to READONLY list."
            )

    if not action_lines:
        action_lines.append("    pass")

    lines = [
        '"""Auto-generated replay script — can be run independently."""',
        "import asyncio",
        "import os",
        "from playwright.async_api import async_playwright",
        "",
        "",
        "async def run(page, context):",
    ]
    lines.extend(action_lines)
    lines.extend([
        "",
        "",
        'if __name__ == "__main__":',
        "    async def main():",
        "        pw = await async_playwright().start()",
        '        headless = (os.getenv("SKIRITAI_HEADLESS") or os.getenv("HEADLESS", "false")).lower() in ("true", "1", "yes")',
        "        browser = await pw.chromium.launch(headless=headless)",
        "        ctx = await browser.new_context()",
        "        page = await ctx.new_page()",
        "        try:",
        "            await run(page, ctx)",
        "        finally:",
        "            await browser.close()",
        "            await pw.stop()",
        "",
        "    asyncio.run(main())",
    ])
    return "\n".join(lines)


def _action_to_line(action: str, args: dict) -> str | None:
    """Convert a single tool action to a Playwright Python line. Returns None if unrecognized."""
    if action == "navigate":
        url = _esc(args.get("url", ""))
        return '\n'.join([
            f'    await page.goto("{url}")',
            f'    await page.wait_for_load_state("networkidle")',
        ])

    if action == "click":
        return f'    await page.click("{_esc(args.get("selector", ""))}")'

    if action == "click_force":
        return f'    await page.click("{_esc(args.get("selector", ""))}", force=True)'

    if action == "fill":
        return f'    await page.fill("{_esc(args.get("selector", ""))}", "{_esc(args.get("text", ""))}")'

    if action == "type_text":
        return f'    await page.locator("{_esc(args.get("selector", ""))}").press_sequentially("{_esc(args.get("text", ""))}")'

    if action == "focus":
        return f'    await page.locator("{_esc(args.get("selector", ""))}").focus()'

    if action == "wait_for":
        timeout = args.get("timeout", 5000)
        return f'    await page.wait_for_selector("{_esc(args.get("selector", ""))}", timeout={timeout})'

    if action == "scroll":
        direction = args.get("direction", "down")
        amount = args.get("amount", 500)
        y = amount if direction == "down" else -amount
        return f"    await page.mouse.wheel(0, {y})"

    if action == "eval_js":
        expr = args.get("expression", "")
        # Use repr() for safe embedding of arbitrary JS in Python source.
        # repr() handles all edge cases: quotes, backticks, newlines, etc.
        return f"    result = await page.evaluate({repr(expr)})"

    if action == "select_option":
        return f'    await page.select_option("{_esc(args.get("selector", ""))}", "{_esc(args.get("value", ""))}")'

    if action == "hover":
        return f'    await page.hover("{_esc(args.get("selector", ""))}")'

    if action == "screenshot":
        return f'    await page.screenshot(path="{_esc(args.get("name", "screenshot"))}.png", full_page=True)'

    return None


def _esc(s: str) -> str:
    """Escape a string for safe embedding in a double-quoted Python source literal.

    Handles: backslashes, double quotes, newlines, carriage returns, tabs,
    backticks (template literals), and ${} expressions.
    """
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
