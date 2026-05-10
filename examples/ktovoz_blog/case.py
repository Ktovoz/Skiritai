"""Test ktovoz.com personal blog — long-range AI-driven test with 12 steps.

Demonstrates Skiritai's key capabilities for long-range testing:
- Pure natural-language AI exploration (no hardcoded selectors)
- Lifecycle hooks for observability
- Failure policies for optional steps
- Cross-step flow: navigation, discovery, verification, summary
"""

from skiritai.core.base_case import BaseCase, FailurePolicy, on_failure


class KtovozBlogCase(BaseCase):
    """Long-range test of ktovoz.com — AI explores and verifies a real personal blog.

    This test demonstrates that Skiritai can handle complex, multi-step
    browser test scenarios using pure natural language — no knowledge
    of the site's DOM structure is required upfront.
    """

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    # ---- Phase 1: Homepage Discovery ----

    async def open_homepage(self):
        """Navigate to https://ktovoz.com and wait for the page to fully load."""
        await self.ai.action("打开 https://ktovoz.com 首页，等待页面完全加载")

    async def verify_homepage_loaded(self):
        """Verify the homepage shows title, navigation, and main content area."""
        await self.ai.action(
            "在当前页面（https://ktovoz.com）上检查并确认："
            "1) 页面标题存在且包含博客相关文字 "
            "2) 导航栏可见（如 Blog, About 等链接） "
            "3) 页面有文章列表或主要内容区域"
        )

    async def discover_navigation(self):
        """Analyze all navigation links, pages, and tag/category entries."""
        await self.ai.action(
            "在 https://ktovoz.com 首页，使用 analyze_page 获取所有链接和导航项。"
            "列出：1) 主导航有哪些页面 2) 首页显示了几篇文章 "
            "3) 有哪些标签/分类入口。将所有发现整理成清单后输出。"
        )

    # ---- Phase 2: Article Detail ----

    async def open_first_article(self):
        """Click the first article title to enter its detail page."""
        await self.ai.action(
            "在 https://ktovoz.com 首页，用 click_text 点击第一篇文章的标题文字，"
            "进入文章详情页面"
        )

    async def verify_article_detail(self):
        """Verify the article detail page contains title, date, body, and tags."""
        await self.ai.action(
            "你现在应该在一个文章详情页（URL 包含 /blog/）。请在这个页面检查："
            "1) 是否有文章标题 2) 是否有发布日期 "
            "3) 是否有正文内容 4) 是否有标签/分类。逐项确认后报告。"
        )

    # ---- Phase 3: Navigation & Sections ----

    async def return_to_homepage(self):
        """Navigate back to the homepage."""
        await self.ai.action(
            "通过点击导航栏中的 'Kto-Blog' 或博客 logo 链接，返回 https://ktovoz.com 首页"
        )

    async def visit_about_page(self):
        """Navigate to the About page and verify its content."""
        await self.ai.action(
            "从 https://ktovoz.com 首页，找到并点击 'About' 导航链接，"
            "进入关于页面。确认页面上是否展示了博主信息：头像、个人简介、社交链接等。"
            "逐项报告发现的内容。"
        )

    async def explore_tags(self):
        """Browse one tag page and verify filtered articles."""
        await self.ai.action(
            "回到 https://ktovoz.com 首页，找到一个标签/分类链接（如 C++, Go, Learning 等），"
            "点击该标签进入标签归档页。确认：该页面的文章列表已按标签筛选，"
            "且显示的文章与标签主题相关。报告你选择的标签和看到的文章数量。"
        )

    # ---- Phase 4: Footer & Search ----

    async def verify_footer(self):
        """Scroll to page bottom and verify footer content."""
        await self.ai.action(
            "回到 https://ktovoz.com 首页，滚动到页面最底部。"
            "检查页脚区域：是否有版权信息、是否有社交链接或 RSS 订阅入口。"
            "报告页脚中所有可见信息。"
        )

    @on_failure(FailurePolicy.SKIP)
    async def test_search(self):
        """Test search functionality if available on the site (optional)."""
        await self.ai.action(
            "在 https://ktovoz.com 首页上寻找搜索入口（搜索框或搜索图标）。"
            "如果找到，输入关键词 'GCC' 进行搜索，检查搜索结果是否返回了相关文章。"
            "如果没有搜索功能，直接返回 '搜索功能不可用' 并标记为跳过。"
            "注意：只能在 ktovoz.com 域名下操作，不要导航到其他网站。"
        )

    # ---- Phase 5: Final Summary ----

    async def final_review(self):
        """Return to homepage and produce a comprehensive test summary."""
        await self.ai.action(
            "返回 https://ktovoz.com 首页。基于本次测试中发现的所有信息，"
            "给出一份总结报告：网站主题是什么、有哪些主要页面、"
            "大约有多少篇文章、覆盖了哪些标签/分类、网站功能是否正常。"
        )

    # ---- Hooks: observability for long-range tests ----

    async def before_step(self, step_name: str):
        print(f"\n{'='*40}")
        print(f"[KtovozBlog] >>> Starting: {step_name}")
        print(f"[KtovozBlog] Phase: {self.ctx.phase.value}")
        print(f"[KtovozBlog] Completed: {len(self.ctx.completed_steps)} steps")

    async def after_step(self, step_name: str, result: dict):
        success = result.get("success", False)
        status = "OK" if success else "FAIL"
        summary = result.get("summary", "")[:100]
        print(f"[KtovozBlog] <<< Done: {step_name} [{status}] — {summary}")
