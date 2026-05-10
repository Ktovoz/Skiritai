"""演示 self.ctx 跨步骤上下文共享。

运行：skiritai run examples/context_demo
"""
from skiritai.core.base_case import BaseCase


class ContextDemoCase(BaseCase):

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    async def step1_write_context(self):
        """在 ctx.store 中写入数据，后续步骤可读取。"""
        await self.ai.action("导航到 httpbin.org 首页")

        # 用 .set() / .get() 方法操作跨步骤存储
        self.ctx.store.set("home_url", self.page.url)
        self.ctx.store.set("started_at", str(self.ctx.elapsed_seconds))

        print(f"  phase={self.ctx.phase.value}")
        print(f"  browser_mode={self.ctx.browser.mode}")

        return {"success": True, "summary": f"已写入上下文: home_url={self.ctx.store.get('home_url')}"}

    async def step2_read_context(self):
        """从 ctx.store 中读取上一步写入的数据。"""
        home_url = self.ctx.store.get("home_url", "未设置")
        started = self.ctx.store.get("started_at", "未设置")

        print(f"  已完成步骤: {self.ctx.completed_steps}")
        print(f"  已耗时: {self.ctx.elapsed_seconds:.1f}s")

        # 基于上下文数据做进一步操作
        await self.ai.action(f"确认当前页面依然可以正常访问，URL 正确")

        return {"success": True, "summary": f"读取上下文: home_url={home_url}"}
