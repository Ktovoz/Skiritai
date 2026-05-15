"""抖音精选搜索 — flow() 函数式 API + 代码显式创建 Provider。

用 flow() 函数式风格完成抖音搜索测试，同时在代码中显式配置 LLM。
适合不需要 BaseCase 生命周期管理的场景。

运行：
    python examples/advanced/douyin_search/02_flow/demo.py
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

    async with flow(results_dir=Path("results/douyin_flow"), llm=llm) as ai:
        # 打开首页
        await ai.action("打开 https://www.douyin.com/jingxuan 首页")

        # 关闭登录弹窗
        await ai.action("关闭页面上的登录弹窗")
        await ai.screenshot("homepage")

        # 搜索流程
        await ai.action(
            "在页面顶部中间位置找到搜索框，点击搜索框使其获得焦点，"
            "然后输入关键词'陈伯全能王'，输入完成后按 Enter 键提交搜索。"
            "确认页面已跳转到搜索结果页面。"
        )
        await ai.screenshot("search_result")

        # 验证搜索结果
        result = await ai.verify("搜索结果页面显示了与'陈伯全能王'相关的内容")
        print(f"搜索验证: {'PASS' if result['passed'] else 'FAIL'} — {result['reason']}")

        # 截图保存最终状态
        await ai.screenshot("final_state")


if __name__ == "__main__":
    asyncio.run(main())
