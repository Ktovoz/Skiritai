"""百度搜索 — BaseCase + 本地 MLX 模型。

使用本地运行的 Qwen3.5-0.8B（MLX），通过 skiritai.toml 配置连接。
零云端依赖，适合离线开发测试。

前置条件：
    python /Users/Joeshen/Dpan/code/tools/aimodel/tests/compatibility/mac/serve.py

运行：
    # 方式1: CLI + --config 指定配置文件
    skiritai run examples/beginner/baidu_search/04_local_model --config examples/beginner/baidu_search/04_local_model/skiritai.toml

    # 方式2: 直接运行 Python（case.py 内部已指定 from_file）
    python examples/beginner/baidu_search/04_local_model/case.py
"""
import asyncio
from pathlib import Path

from skiritai import create_llm
from skiritai.core.base_case import BaseCase


class BaiduSearchCase(BaseCase):
    """百度搜索测试用例 — 本地模型驱动。"""

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def open_baidu(self):
        """打开百度首页。"""
        await self.ai.action(
            "导航到 https://www.baidu.com，"
            "确认页面标题包含'百度'两字，"
            "然后确认页面中有可以输入搜索内容的区域"
        )

    async def search_keyword(self):
        """搜索关键词。"""
        await self.ai.action(
            "在搜索框中输入关键词'Playwright 自动化测试'，然后点击搜索按钮"
        )

    async def verify_results(self):
        """验证搜索结果。"""
        await self.ai.action(
            "检查搜索结果页面是否正常加载，"
            "确认页面中包含与搜索关键词相关的搜索结果"
        )


if __name__ == "__main__":
    llm = create_llm(from_file=Path(__file__).parent / "skiritai.toml")
    asyncio.run(BaiduSearchCase(case_dir=Path(__file__).parent, llm=llm).run())
