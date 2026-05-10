"""Auto-generated replay script — can be run independently."""
import asyncio
import os
from playwright.async_api import async_playwright


async def run(page, context):
    await page.goto("https://httpbin.org/")
    await page.wait_for_load_state("networkidle")
    result = await page.evaluate("Array.from(document.querySelectorAll('h4.opblock-tag')).map(h=>h.textContent.trim())")
    result = await page.evaluate("Array.from(document.querySelectorAll('.opblock-summary')).length")
    result = await page.evaluate("Array.from(document.querySelectorAll('section.opblock-tag-section')).map(s=>({open:s.classList.contains('is-open'), title:s.querySelector('h4.opblock-tag')?.textContent.trim()}))")
    result = await page.evaluate("Array.from(document.querySelectorAll('a')).map(a=>({text:a.textContent.trim(), href:a.getAttribute('href')}))")
    await page.click("text=HTTP Methods")
    await page.wait_for_selector(".opblock-tag-section.is-open", timeout=5000)
    result = await page.evaluate("Array.from(document.querySelectorAll('.opblock-tag-section.is-open .opblock-summary')).map(n=>n.textContent.trim())")


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