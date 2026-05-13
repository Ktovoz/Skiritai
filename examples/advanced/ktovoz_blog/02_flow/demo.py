"""ktovoz.com 博客测试 — flow() 函数式 API + 代码显式创建 Provider。

用 flow() 函数式风格完成博客测试，同时在代码中显式配置 LLM。
适合不需要 BaseCase 生命周期管理的场景。

运行：
    python examples/advanced/ktovoz_blog/02_flow/demo.py
"""
import asyncio
import os
from pathlib import Path

from skiritai import flow
from skiritai.llm import OpenAIProvider


async def main():
    llm = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("LLM_MODEL", "gpt-4o"),
    )

    async with flow(results_dir=Path("results/ktovoz_flow"), llm=llm) as ai:
        # 首页
        await ai.action("打开 https://ktovoz.com 首页")
        await ai.screenshot("homepage")
        await ai.verify("页面标题包含博客相关文字，导航栏可见")

        # 文章详情
        await ai.action("点击第一篇文章，进入文章详情页")
        await ai.screenshot("article_detail")
        await ai.verify("页面显示了文章标题、发布日期和正文内容")

        # About 页面
        await ai.action("返回首页，点击导航栏的 About 链接")
        await ai.screenshot("about_page")

        # 搜索
        await ai.action("返回首页，在右上角找到搜索按钮（放大镜图标），点击后输入 'GCC' 并回车")
        await ai.screenshot("search_result")

        # 页脚
        await ai.action("返回首页，滚动到页面最底部")
        await ai.verify("页脚区域包含版权信息")
        await ai.screenshot("footer")


if __name__ == "__main__":
    asyncio.run(main())
