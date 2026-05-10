"""演示三种失败策略：ABORT（默认）、SKIP（跳过）、RETRY（重试）。

运行：skiritai run examples/failure_policies
"""
from skiritai.core.base_case import BaseCase, on_failure, FailurePolicy


class FailurePoliciesCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    # ABORT（默认）：任何步骤失败都会停止整个用例
    async def normal_step(self):
        await self.ai.action("导航到 httpbin.org 首页")
        return {"success": True, "summary": "普通步骤完成"}

    # SKIP：非关键步骤，失败后跳过，不影响后续步骤
    @on_failure(FailurePolicy.SKIP)
    async def optional_check(self):
        await self.ai.action("检查页面上是否有 'forms' 相关的链接")
        return {"success": True, "summary": "可选检查完成"}

    # RETRY：偶发性失败时自动重试，最多重试 2 次（共执行 3 次）
    @on_failure(FailurePolicy.RETRY, max_retries=2)
    async def flaky_step(self):
        await self.ai.action("确认 httpbin.org 首页标题可见，页面正在正常加载")
        return {"success": True, "summary": "重试步骤完成"}
