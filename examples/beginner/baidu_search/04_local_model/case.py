"""百度搜索 — BaseCase + 本地 MLX 模型。

使用本地运行的 Qwen3.5-0.8B（MLX OpenAI 兼容服务），通过 OpenAIProvider
直接配置连接。零云端依赖，适合离线开发测试。

前置条件：
    python /Users/Joeshen/Dpan/code/tools/aimodel/tests/compatibility/mac/serve.py

运行：
    # 方式1: CLI + --config 指定配置文件
    skiritai run examples/beginner/baidu_search/04_local_model --config examples/beginner/baidu_search/04_local_model/skiritai.toml

    # 方式2: 直接运行 Python（内部通过 OpenAIProvider + 环境变量配置）
    python examples/beginner/baidu_search/04_local_model/case.py

环境变量（可选）：
    OPENAI_API_KEY  — API 密钥（默认 local）
    OPENAI_BASE_URL — API 地址（默认 http://127.0.0.1:8901/v1）
    LLM_MODEL       — 模型名称（默认 Qwen3.5-0.8B）
"""
import asyncio
import os
from pathlib import Path

from skiritai import create_llm
from skiritai import flow
from skiritai.core.base_case import BaseCase
from skiritai.llm import OpenAIProvider

async def main():

    llm = create_llm(from_file=Path(__file__).parent / "skiritai.toml")

    async with flow(results_dir=Path("results/baidu_flow"), llm=llm) as ai:
        await ai.action("打开百度首页 https://www.baidu.com，确认页面标题包含'百度'")
        await ai.screenshot("homepage")

        await ai.action("在搜索框中输入'Playwright 自动化测试'并点击搜索按钮")
        await ai.screenshot("search_result")

        result = await ai.verify("搜索结果页面包含与 Playwright 相关的内容")
        print(f"验证结果: {'PASS' if result['passed'] else 'FAIL'} — {result['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
