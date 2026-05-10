"""Auto-generated replay script — can be run independently."""
import asyncio
import os
from playwright.async_api import async_playwright


async def run(page, context):
    result = await page.evaluate("(() => {\n  const kwEn = 'playwright';\n  const kwZh = '自动化测试';\n  const bodyText = document.body.innerText || '';\n  const hasEn = bodyText.toLowerCase().includes(kwEn);\n  const hasZh = bodyText.includes(kwZh);\n  const nodes = Array.from(document.querySelectorAll('a, h3, h2'))\n    .filter(el => (el.textContent || '').toLowerCase().includes(kwEn));\n  const samples = nodes.slice(0, 5).map(el => el.textContent.trim()).filter(Boolean);\n  return { hasEn, hasZh, count: nodes.length, samples };\n})();")


if __name__ == "__main__":
    async def main():
        pw = await async_playwright().start()
        headless = (os.getenv("SKIRITAI_HEADLESS") or os.getenv("HEADLESS", "false")).lower() in ("true", "1", "yes")
        browser = await pw.chromium.launch(headless=headless)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        try:
            await run(page, ctx)
        finally:
            await browser.close()
            await pw.stop()

    asyncio.run(main())