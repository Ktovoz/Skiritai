"""抖音精选搜索 — BaseCase 类方式 + 环境变量 LLM 配置。

进阶示例，展示在复杂 SPA 页面上的测试能力：
- 抖音精选页面动态内容加载
- 登录弹窗处理（dismiss_overlay 工具）
- 搜索框交互
- 搜索结果验证
- 生命周期钩子
- 失败策略

运行：
    skiritai run examples/advanced/douyin_search/01_basecase
    python examples/advanced/douyin_search/01_basecase/case.py
"""
import asyncio
from pathlib import Path

from skiritai.core.base_case import BaseCase, FailurePolicy, on_failure


class DouyinSearchCase(BaseCase):
    """抖音精选搜索测试用例。"""

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    # ---- 首页加载 ----

    async def open_homepage(self):
        """打开抖音精选首页。"""
        await self.ai.action("打开 https://www.douyin.com/jingxuan 首页")

    async def dismiss_popup(self):
        """关闭登录弹窗。"""
        await self.ai.action("关闭页面上的登录弹窗")

    async def verify_homepage(self):
        """验证首页内容。"""
        await self.ai.screenshot("homepage")
        await self.ai.analyze_page()
        await self.ai.verify("页面顶部有搜索框，页面主体区域展示了视频卡片内容")

    # ---- 搜索功能 ----

    async def search_keyword(self):
        """搜索关键词。"""
        await self.ai.action(
            "在搜索框中输入'陈伯全能王'，然后点击搜索按钮（不是侧边栏的搜索，是搜索框旁边的搜索按钮），"
            "确认页面跳转到搜索结果页面（URL 包含 search）"
        )
        await self.ai.screenshot("search_result")

    # ---- 搜索结果验证 ----

    async def verify_search_results(self):
        """验证搜索结果页面。"""
        await self.ai.analyze_page()
        await self.ai.verify("页面已跳转到搜索结果页面，显示了与'陈伯全能王'相关的搜索结果")

    @on_failure(FailurePolicy.SKIP)
    async def check_user_profile(self):
        """尝试进入用户主页。"""
        await self.ai.action(
            "在搜索结果中找到'陈伯全能王'相关的用户或视频，"
            "点击进入查看详情。如果无法找到确切匹配，说明情况并跳过。"
        )
        await self.ai.screenshot("user_detail")

    # ---- 钩子 ----

    async def before_step(self, step_name: str):
        print(f"\n{'='*40}")
        print(f"[DouyinSearch] >>> {step_name}")

    async def after_step(self, step_name: str, result: dict):
        status = "OK" if result.get("success") else "FAIL"
        elapsed = result.get("elapsed", 0)
        print(f"[DouyinSearch] <<< {step_name} [{status}] ({elapsed:.1f}s)")


if __name__ == "__main__":
    asyncio.run(DouyinSearchCase(case_dir=Path(__file__).parent).run())
