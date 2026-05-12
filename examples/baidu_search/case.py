"""百度搜索测试用例 —— AI 驱动，自然语言描述操作意图。

步骤只需定义为 async def foo(self)，用 self.ai.action() 描述操作。
无需 @step 装饰器，所有公共方法自动检测为步骤。

框架自动加载 .env 并注册工具，无需任何手动初始化。

运行方式：
    skiritai run examples/baidu_search    # CLI（推荐）
    python examples/baidu_search/case.py  # 直接运行
"""
import asyncio
from pathlib import Path

from skiritai.core.base_case import BaseCase


class BaiduSearchCase(BaseCase):
    """百度搜索测试用例。"""

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_baidu(self):
        """打开百度首页。"""
        await self.ai.action("导航到 https://www.baidu.com，确认页面标题包含'百度'两字，然后确认页面中有可以输入搜索内容的区域")

    async def search_keyword(self):
        """搜索关键词 —— 纯自然语言，AI 自行找到搜索框和按钮。"""
        await self.ai.action("在页面上的搜索框中输入关键词'Playwright 自动化测试'，然后点击搜索按钮")

    async def verify_results(self):
        """验证搜索结果。"""
        await self.ai.action("检查搜索结果页面是否正常加载，确认页面中包含与搜索关键词相关的搜索结果")


if __name__ == "__main__":
    # ---- 默认方式：自动从 .env / 环境变量读取 LLM 配置 ----
    asyncio.run(BaiduSearchCase(case_dir=Path(__file__).parent).run())

    # ---- 显式方式：代码指定 LLM provider ----
    # from skiritai.llm import OpenAIProvider
    # llm = OpenAIProvider(
    #     api_key="sk-xxx",
    #     base_url="https://api.gptsapi.net/v1",
    #     model="gpt-5",
    # )
    # asyncio.run(BaiduSearchCase(case_dir=Path(__file__).parent, llm=llm).run())
