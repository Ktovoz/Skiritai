"""抖音精选搜索 — YAML 声明式 + skiritai.toml 配置文件。

用 YAML 定义测试步骤，用 skiritai.toml 配置 LLM。
框架自动发现目录下的 skiritai.toml 加载配置。

运行：
    skiritai run examples/advanced/douyin_search/03_yaml
    python examples/advanced/douyin_search/03_yaml/run.py
"""
import asyncio
from pathlib import Path

from skiritai import run_yaml_case


if __name__ == "__main__":
    report = asyncio.run(run_yaml_case(Path(__file__).parent))
    print(f"结果: {report['status']} — {report['success_count']}/{report['total_steps']} 通过")
