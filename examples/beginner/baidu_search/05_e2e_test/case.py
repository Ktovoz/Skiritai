"""百度搜索 — E2E 测试（验证报告生成）。

使用项目环境配置的模型运行 flow，验证：
  1. 报告使用新版 Vue 模板（而非旧版静态模板）
  2. 每个 step 附带 summary / assertion 等信息
  3. 截图正确嵌入到报告 HTML 中

运行：
    python examples/beginner/baidu_search/05_e2e_test/case.py
"""
import asyncio
import json
from pathlib import Path

from skiritai import flow

RESULTS_DIR = Path(__file__).parent / "results"


async def main():
    async with flow(results_dir=RESULTS_DIR, llm=None) as ai:
        await ai.action("打开百度首页 https://www.baidu.com")
        await ai.screenshot("homepage")

        await ai.action("在搜索框中输入'Playwright 自动化测试'并点击搜索按钮")
        await ai.screenshot("search_result")

        result = await ai.verify("搜索结果页面包含与 Playwright 相关的内容")
        print(f"验证结果: {'PASS' if result['passed'] else 'FAIL'} — {result['reason']}")

    # ---- 验证报告内容 ----
    _check_report(RESULTS_DIR)


def _check_report(results_dir: Path) -> None:
    ts_dirs = sorted((results_dir / "test_results").iterdir(), reverse=True)
    if not ts_dirs:
        print("ERROR: 未找到报告目录")
        return

    latest = ts_dirs[0]
    report_json = json.loads((latest / "report.json").read_text())
    report_html = (latest / "report.html").read_text()

    errors = []

    # 1. 新版 Vue 模板检测
    if "report-data" not in report_html:
        errors.append("使用了旧版静态模板（无 report-data script tag）")
    elif '{"placeholder":true}' in report_html:
        errors.append("报告数据未正确嵌入 Vue 模板")

    # 2. Step 信息完整性
    for step in report_json["steps"]:
        sid = step.get("step_id", "?")
        stype = step.get("type", "?")

        if stype == "action":
            if not step.get("summary"):
                errors.append(f"Step {sid} (action): 缺少 summary")
        elif stype == "verify":
            if not step.get("assertion"):
                errors.append(f"Step {sid} (verify): 缺少 assertion")
            if not step.get("reason"):
                errors.append(f"Step {sid} (verify): 缺少 reason")

    # 3. 截图文件存在 + HTML 中 base64 嵌入
    ss_count = 0
    for step in report_json["steps"]:
        sid = step.get("step_id", "?")
        for s in step.get("screenshots", []):
            ss_count += 1
            path = s.get("path", "")
            if not path.startswith("data:") and not Path(path).exists():
                errors.append(f"Step {sid}: 截图文件不存在 (path={path[:100]})")
    if ss_count == 0:
        errors.append("报告中没有任何截图")

    # 4. HTML 报告中截图是否嵌入
    b64_count = report_html.count("data:image/png;base64,")
    if b64_count < ss_count:
        errors.append(f"HTML 中 base64 截图数量不足: {b64_count}/{ss_count}")

    if errors:
        print("\n--- 报告检查 FAIL ---")
        for e in errors:
            print(f"  x {e}")
    else:
        print("\n--- 报告检查 PASS ---")


if __name__ == "__main__":
    asyncio.run(main())
