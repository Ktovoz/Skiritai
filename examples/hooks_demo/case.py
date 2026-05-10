"""演示三个钩子：before_step、after_step、on_step_error + StepResult。

运行：skiritai run examples/hooks_demo
"""
from skiritai.core.base_case import BaseCase, on_failure, FailurePolicy, StepResult


class HooksDemoCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    # ---- 钩子 ----

    async def before_step(self, step_name: str) -> None:
        print(f"[before_step] → {step_name}")

    async def after_step(self, step_name: str, result: dict) -> None:
        status = "✓" if result.get("success") else "✗"
        print(f"[after_step]  ← {step_name} {status}")

    async def on_step_error(self, step_name: str, error: Exception) -> StepResult:
        """步骤失败时调用。返回 StepResult 控制行为：
            StepResult.continue_() — 标记失败，由 @on_failure 策略决定
            StepResult.do_skip()   — 跳过此步骤
            StepResult.do_retry()  — 重试此步骤
        """
        print(f"[on_step_error] {step_name}: {error}")
        return StepResult.continue_()

    # ---- 步骤 ----

    async def success_step(self):
        """正常步骤：导航到 httpbin.org。"""
        await self.ai.action("导航到 httpbin.org 首页")
        return {"success": True, "summary": "正常步骤完成"}

    async def second_step(self):
        """查看页面信息。"""
        await self.ai.action("获取当前页面的 URL 地址")
        return {"success": True, "summary": "第二步完成"}
