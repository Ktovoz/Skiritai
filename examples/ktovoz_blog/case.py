"""Test ktovoz.com personal blog — long-range AI-driven test with 12 steps.

Demonstrates Skiritai's key capabilities for long-range testing:
- Pure natural-language AI exploration (no hardcoded selectors)
- Cross-step context sharing via self.ctx.store
- Lifecycle hooks for observability
- Failure policies for optional steps
- Mixed explore/replay modes for different step types
"""

from skiritai.core.base_case import BaseCase, FailurePolicy, on_failure, step_mode


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

    # ---- Phase 1: Site Discovery ----

    async def open_homepage(self):
        """Open the blog homepage and wait for it to load."""
        await self.ai.action("打开 https://ktovoz.com 首页，等待页面完全加载")

    async def verify_homepage_loaded(self):
        """Verify the homepage renders correctly with key elements."""
        await self.ai.action(
            "确认首页已成功加载：检查页面标题是否存在、"
            "是否有导航栏、是否有文章列表或主要内容区域"
        )

    async def discover_site_structure(self):
        """Use AI to analyze and record the site's navigation structure."""
        await self.ai.action(
            "使用 analyze_page 分析页面，记录网站有哪些页面链接、"
            "导航菜单包含哪些项目、页面上有哪些分类或标签入口。"
            "将发现的页面数量保存到上下文。"
        )

    # ---- Phase 2: Article Browsing ----

    async def browse_article_list(self):
        """Browse the article listing and count visible articles."""
        await self.ai.action(
            "浏览首页的文章列表，数一数当前页面显示了多少篇文章，"
            "并记录第一篇文章的标题文本"
        )

    async def open_first_article(self):
        """Click through to the first article's detail page."""
        await self.ai.action(
            "点击第一篇文章的标题链接，进入文章详情页面"
        )

    async def verify_article_detail(self):
        """Verify the article detail page has all expected elements."""
        await self.ai.action(
            "确认文章详情页包含以下要素：文章标题、发布日期或时间、"
            "文章正文内容、以及可能的标签或分类信息"
        )

    # ---- Phase 3: Navigation & Site Features ----

    async def return_to_homepage(self):
        """Navigate back to the homepage."""
        await self.ai.action("返回网站首页")

    async def explore_categories(self):
        """Explore category or tag pages to verify content organization."""
        await self.ai.action(
            "找到文章分类或标签的入口，点击其中一个分类，"
            "确认该分类下的文章列表正确显示，且每篇文章都属于该分类"
        )

    async def visit_about_page(self):
        """Visit the About page and verify personal info is present."""
        await self.ai.action(
            "访问关于页面（About），查看博主个人信息是否完整，"
            "包括头像、简介、社交链接等"
        )

    # ---- Phase 4: Optional & Edge Cases ----

    @on_failure(FailurePolicy.SKIP)
    async def test_search(self):
        """Test the search functionality if available (skip if not present)."""
        await self.ai.action(
            "找到搜索入口，输入一个可能存在的关键词进行搜索，"
            "检查搜索结果页面是否返回了相关内容"
        )

    @step_mode("explore")
    async def explore_random_article(self):
        """Randomly explore another article to verify consistency."""
        await self.ai.action(
            "返回文章列表页面，随机选择另一篇文章打开，"
            "确认文章内容完整、排版正常、没有明显的渲染问题"
        )

    async def verify_footer(self):
        """Scroll to the bottom and check the footer section."""
        await self.ai.action(
            "滚动到页面最底部，检查页脚区域是否包含版权信息、"
            "备案号（如果有）、以及社交媒体或 RSS 链接"
        )

    # ---- Phase 5: Summary ----

    async def final_review(self):
        """Return to homepage and provide a final summary of the test."""
        await self.ai.action(
            "返回首页，回顾本次测试中发现的所有页面和功能，"
            "总结：网站包含哪些页面类型、有多少篇文章、"
            "哪些功能正常工作、是否有任何异常"
        )

    # ---- Hooks: observability for long-range tests ----

    async def before_step(self, step_name: str):
        print(f"\n{'='*40}")
        print(f"[KtovozBlog] >>> Starting: {step_name}")
        print(f"[KtovozBlog] Phase: {self.ctx.phase.value}")
        print(f"[KtovozBlog] Completed so far: {len(self.ctx.completed_steps)} steps")

    async def after_step(self, step_name: str, result: dict):
        success = result.get("success", False)
        status = "OK" if success else "FAIL"
        summary = result.get("summary", "")[:100]
        print(f"[KtovozBlog] <<< Done: {step_name} [{status}] — {summary}")
