"""Minimal example — pure Playwright, no AI required.

This case demonstrates the simplest usage of Skiritai:
a case that runs Playwright steps directly without any LLM calls.
Each step uses self.page (Playwright Page API) instead of self.ai.action().

Run:
    skiritai run examples/minimal
"""
from skiritai.core.base_case import BaseCase


class MinimalCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def s1_navigate(self):
        """Navigate to example.com and verify the title."""
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state("networkidle")
        title = await self.page.title()
        assert "Example" in title, f"Unexpected title: {title}"
        return {"success": True, "summary": f"已导航到 {self.page.url}"}

    async def s2_check_heading(self):
        """Verify the h1 heading text."""
        heading = await self.page.locator("h1").text_content()
        assert heading and "Example" in heading, f"Unexpected heading: {heading}"
        return {"success": True, "summary": f"标题: {heading}"}

    async def s3_follow_link(self):
        """Click the link and verify navigation."""
        await self.page.locator("a").click()
        await self.page.wait_for_load_state("networkidle")
        url = self.page.url
        assert "iana.org" in url, f"Unexpected URL: {url}"
        return {"success": True, "summary": f"已跳转到 {url}"}
