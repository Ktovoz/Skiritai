"""Flow API 示例 — 无需继承 BaseCase，直接函数式调用。

运行方式：
    python examples/flow_demo/demo.py
"""
import asyncio
from pathlib import Path

from skiritai import flow


async def main():
    async with flow(results_dir=Path("results/flow_demo")) as ai:
        await ai.action("打开百度首页 https://www.baidu.com，确认页面标题包含'百度'")
        await ai.screenshot("homepage")

        await ai.action("在搜索框中输入'Playwright 自动化测试'并点击搜索按钮")
        await ai.screenshot("search_result")

        result = await ai.verify("搜索结果页面包含与 Playwright 相关的内容")
        print(f"验证结果: {'PASS' if result['passed'] else 'FAIL'} — {result['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
