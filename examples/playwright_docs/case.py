"""Playwright 文档测试用例"""
from skiritai.core.base_case import BaseCase


class PlaywrightDocsCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_docs(self, ai):
        await ai.action("导航到 Playwright Python 文档首页，等待页面加载完成")

    async def get_page_title(self, ai):
        await ai.action("获取当前页面的标题和 URL")

    async def click_get_started(self, ai):
        await ai.action("点击页面上的 'Get started' 链接，进入安装指南页面")
