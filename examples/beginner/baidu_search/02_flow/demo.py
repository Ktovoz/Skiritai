"""百度搜索 — flow() 函数式 API + 代码显式创建 Provider。

展示如何用 flow() 函数式 API 编写测试，并在代码中显式创建 LLM Provider。
适合不想继承 BaseCase、偏好函数式风格的场景。

运行：
    python examples/beginner/baidu_search/02_flow/demo.py
"""
import asyncio
import os
from pathlib import Path

from skiritai import flow
from skiritai.llm import OpenAIProvider


async def main():
    # 显式创建 Provider — 可自由切换模型、base_url
    llm = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("LLM_MODEL", "gpt-4o"),
    )

    async with flow(results_dir=Path("results/baidu_flow"), llm=llm) as ai:
        await ai.action("打开百度首页 https://www.baidu.com，确认页面标题包含'百度'")
        await ai.screenshot("homepage")

        await ai.action("在搜索框中输入'Playwright 自动化测试'并点击搜索按钮")
        await ai.screenshot("search_result")

        result = await ai.verify("搜索结果页面包含与 Playwright 相关的内容")
        print(f"验证结果: {'PASS' if result['passed'] else 'FAIL'} — {result['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
