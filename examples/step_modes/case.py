"""演示三种执行模式：auto（默认）、explore（强制探索）、replay（仅回放）。

运行：skiritai run examples/step_modes
"""
from skiritai.core.base_case import BaseCase, step_mode, on_failure, FailurePolicy


class StepModesCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    # auto 模式（默认）：有回放脚本就用，没有就 AI 探索
    async def auto_mode(self):
        await self.ai.action("导航到 httpbin.org 首页，等待页面加载完成")
        return {"success": True, "summary": "auto 模式完成"}

    # explore 模式：始终调用 AI，即使已有回放脚本也会重新探索并覆盖
    @step_mode("explore")
    async def explore_mode(self):
        await self.ai.action("查看 httpbin.org 首页有哪些可用的 HTTP 测试端点链接")
        return {"success": True, "summary": "explore 模式完成"}

    # replay 模式：仅回放已录制的脚本，不回退 AI
    # 首次运行没有脚本会失败，@on_failure(SKIP) 让它优雅跳过
    @step_mode("replay")
    @on_failure(FailurePolicy.SKIP)
    async def replay_mode(self):
        await self.ai.action("导航到 httpbin.org 首页")
        return {"success": True, "summary": "replay 模式完成"}
