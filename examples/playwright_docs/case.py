"""Playwright 文档测试用例 —— AI 驱动 + step_mode 演示。

运行方式：
    skiritai run examples/playwright_docs
"""
from skiritai.core.base_case import BaseCase, step_mode, on_failure, FailurePolicy


class PlaywrightDocsCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    @step_mode("explore")
    async def open_docs(self):
        """导航到 Playwright Python 文档首页（强制 AI 探索）。"""
        await self.ai.action("导航到 Playwright Python 文档首页，等待页面加载完成")

    async def get_page_title(self):
        """获取当前页面标题和 URL。"""
        await self.ai.action("获取当前页面的标题和 URL")

    @on_failure(FailurePolicy.SKIP)
    async def click_get_started(self):
        """点击 'Get started' 链接（非关键步骤，失败跳过）。"""
        await self.ai.action("点击页面上的 'Get started' 链接，进入安装指南页面")
