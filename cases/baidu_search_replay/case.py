"""百度搜索测试用例 - 回放模式"""
from app.engine.base_case import BaseCase


class BaiduSearchReplayCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_baidu(self, ai):
        await ai.action("导航到百度首页，等待页面加载完成")

    async def search_keyword(self, ai):
        await ai.action("先用 get_page_info 查看页面，然后用 eval_js 执行 document.getElementById('kw').value = 'Playwright 自动化测试'; document.getElementById('su').click(); 来搜索")

    async def verify_results(self, ai):
        await ai.action("验证搜索结果页面加载完成，包含相关结果")
