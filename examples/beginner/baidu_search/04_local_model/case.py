"""百度搜索 — Flow + 本地 MLX 模型。

使用本地运行的 Qwen3.5-0.8B（MLX OpenAI 兼容服务），通过 skiritai.toml
配置文件管理 LLM 连接。零云端依赖，适合离线开发测试。

前置条件：
    python /Users/Joeshen/Dpan/code/tools/aimodel/tests/compatibility/mac/serve.py

运行：
    python examples/beginner/baidu_search/04_local_model/case.py
"""
import asyncio
import os
from pathlib import Path

# 绕过系统代理，确保本地 LLM 请求不被代理拦截
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")

from skiritai import create_llm
from skiritai import flow

async def main():
    llm = create_llm(from_file=Path(__file__).parent / "skiritai.toml")

    async with flow(results_dir=Path("results/baidu_flow"), llm=llm) as ai:
        await ai.action("打开百度首页 https://www.baidu.com")
        await ai.screenshot("homepage")

        await ai.action("在百度搜索框中输入文字 'Playwright 自动化测试'")
        await ai.action("点击搜索按钮")
        await ai.screenshot("search_result")

        result = await ai.verify("搜索结果页面包含与 Playwright 相关的内容")
        print(f"验证结果: {'PASS' if result['passed'] else 'FAIL'} — {result['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
