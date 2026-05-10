"""Auto-generated replay script — can be run independently."""
import asyncio
import os
from playwright.async_api import async_playwright


async def run(page, context):
    result = await page.evaluate("window.scrollTo(0, Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)); 'scrolled';")
    await page.wait_for_selector("body", timeout=5000)
    result = await page.evaluate('window.scrollTo(0, Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)); ({y: window.scrollY, inner: window.innerHeight, h: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)})')
    await page.mouse.wheel(0, 800)


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