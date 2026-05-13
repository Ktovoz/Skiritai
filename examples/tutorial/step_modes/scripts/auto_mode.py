"""Auto-generated replay script — can be run independently."""
import asyncio
import os
from playwright.async_api import async_playwright


async def run(page, context):
    await page.goto("https://httpbin.org/")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_selector("text=A simple HTTP Request & Response Service.", timeout=8000)


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
# acceptance test update
# acceptance test update