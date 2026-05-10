"""Test ktovoz.com personal blog — long-range AI-driven test.

Demonstrates Skiritai's full capability set:
- ai.analyze_page() — pre-load DOM data before AI reasoning
- ai.screenshot(name) — code-controlled screenshots at key moments
- ai.verify(assertion) — AI-powered assertions (non-blocking on failure)
- ai.action() — pure natural language, no tool references
- Lifecycle hooks for observability
- Failure policies for optional steps
"""

from skiritai.core.base_case import BaseCase, FailurePolicy, on_failure


class KtovozBlogCase(BaseCase):
    """Long-range test of ktovoz.com — 11 steps covering a real personal blog.

    Uses the full Skiritai API surface: analyze_page for pre-discovery,
    screenshot for visual evidence, verify for soft assertions,
    and action for natural-language AI exploration.
    """

    async def setup(self):
        await self.launch_browser()

    async def teardown(self):
        await self.close_browser()

    # ---- Phase 1: Homepage Discovery ----

    async def open_homepage(self):
        await self.ai.action("打开 https://ktovoz.com 首页")
        await self.ai.screenshot("homepage")

    async def verify_homepage_loaded(self):
        await self.ai.analyze_page()
        await self.ai.verify("页面标题包含博客相关文字")
        await self.ai.verify("导航栏可见，包含 Blog、About 等链接")
        await self.ai.verify("页面有文章列表或主要内容区域")
        await self.ai.screenshot("homepage_verified")

    async def discover_navigation(self):
        await self.ai.analyze_page()
        await self.ai.get_page_info()
        await self.ai.action(
            "分析当前页面的所有导航链接和页面入口。"
            "列出：1) 主导航有哪些页面 2) 首页显示了几篇文章 3) 有哪些标签或分类。"
            "全部整理成结构化清单输出。"
        )
        await self.ai.screenshot("navigation_discovered")

    # ---- Phase 2: Article Detail ----

    async def open_first_article(self):
        await self.ai.analyze_page()
        await self.ai.action("点击第一篇文章，进入文章详情页")
        await self.ai.screenshot("article_detail")

    async def verify_article_detail(self):
        await self.ai.analyze_page()
        await self.ai.verify("页面显示了文章标题")
        await self.ai.verify("页面显示了发布日期或时间")
        await self.ai.verify("页面包含文章正文内容")

    # ---- Phase 3: Navigation & Sections ----

    async def return_to_homepage(self):
        await self.ai.action("返回网站首页")

    async def visit_about_page(self):
        await self.ai.action("点击导航栏的 About 链接，进入关于页面")
        await self.ai.analyze_page()
        await self.ai.verify("页面包含博主个人信息，如头像或简介")
        await self.ai.screenshot("about_page")

    async def explore_tags(self):
        await self.ai.action("返回首页")
        await self.ai.analyze_page()
        await self.ai.action(
            "点击任意一个标签/分类链接，进入标签页。确认文章列表显示正确，"
            "报告选择的标签名称和该标签下的文章数量。"
        )
        await self.ai.screenshot("tag_page")

    # ---- Phase 4: Search & Footer ----

    async def use_search(self):
        """Click the search button (top-right), type into the modal, and verify results."""
        await self.ai.action("返回首页")
        await self.ai.analyze_page()
        # The blog has a search button (magnifying glass icon, no text) at top-right
        # Use click_text on any search-related text, or click the button element
        await self.ai.action(
            "在页面右上角区域找到搜索按钮。注意：搜索按钮是一个图标按钮，"
            "没有文字，通常显示为放大镜图标。点击它之后会弹出一个搜索框。"
            "在搜索框中输入 'GCC' 并回车。"
            "查看搜索结果页面，确认返回了与 GCC 相关的文章。"
        )
        await self.ai.screenshot("search_result")

    @on_failure(FailurePolicy.SKIP)
    async def test_rss(self):
        """Check if RSS/subscription is available (optional)."""
        await self.ai.action("返回首页")
        await self.ai.action(
            "检查页面上是否有 RSS 订阅链接或邮件订阅入口。"
            "如果没有找到，直接说明并跳过。"
        )

    # ---- Phase 5: Footer & Summary ----

    async def verify_footer(self):
        await self.ai.action("返回首页，滚动到页面最底部")
        await self.ai.verify("页脚区域包含版权信息")
        await self.ai.action("检查页脚中是否有社交链接（如 GitHub、Twitter）和备案号")
        await self.ai.screenshot("footer")

    async def final_review(self):
        await self.ai.action(
            "返回首页。基于本次测试中的所有发现，给出一份完整的总结报告："
            "网站主题是什么、有哪些主要页面、大约有多少篇文章、"
            "覆盖了哪些标签/分类、搜索功能是否可用、网站功能是否正常。"
        )

    # ---- Hooks ----

    async def before_step(self, step_name: str):
        print(f"\n{'='*40}")
        print(f"[KtovozBlog] >>> {step_name}  (completed: {len(self.ctx.completed_steps)})")

    async def after_step(self, step_name: str, result: dict):
        status = "OK" if result.get("success") else "FAIL"
        summary = result.get("summary", "")[:120]
        elapsed = result.get("elapsed", 0)
        print(f"[KtovozBlog] <<< {step_name} [{status}] ({elapsed:.1f}s) — {summary}")
