"""Test: Replay vs Explore mode comparison with report generation."""
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path


from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


# Report data collector
report_data = {
    "timestamp": None,
    "explore": {"time": 0, "status": "", "steps": [], "scripts_generated": 0},
    "replay": {"time": 0, "status": "", "steps": [], "all_replay": False},
    "comparison": {"speedup": 0, "time_saved": 0}
}


async def test_explore_generates_scripts():
    """Test: explore mode generates replay scripts."""
    print("=== Test: Explore Mode Generates Scripts ===")

    from skiritai.core.runner import run_case

    case_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "baidu_search"
    scripts_dir = case_dir / "scripts"

    # Clean existing scripts before test
    if scripts_dir.exists():
        for f in scripts_dir.glob("*.py"):
            f.unlink()

    # Run in explore mode
    print("  Running explore mode...")
    start = time.time()
    report = await run_case(case_dir)
    explore_time = time.time() - start

    print(f"  Time: {explore_time:.2f}s")
    print(f"  Status: {report['status']}")
    print(f"  Steps: {report['success_count']}/{report['total_steps']}")

    # Check scripts were generated
    generated_scripts = list(scripts_dir.glob("*.py")) if scripts_dir.exists() else []
    print(f"  Generated scripts: {len(generated_scripts)}")
    for s in generated_scripts:
        content = s.read_text()
        has_run = "async def run" in content
        has_actions = "await page" in content
        print(f"    - {s.name}: run={has_run}, actions={has_actions}")

    success = (
        report['status'] == 'completed'
        and len(generated_scripts) == report['total_steps']
        and all("async def run" in s.read_text() for s in generated_scripts)
    )

    # Collect report data
    report_data["explore"]["time"] = explore_time
    report_data["explore"]["status"] = "PASS" if success else "FAIL"
    report_data["explore"]["steps"] = report.get("steps", [])
    report_data["explore"]["scripts_generated"] = len(generated_scripts)

    print(f"  {'PASS' if success else 'FAIL'}\n")
    return explore_time, success


async def test_replay_executes_scripts():
    """Test: replay mode directly executes existing scripts."""
    print("=== Test: Replay Mode Executes Scripts ===")

    from skiritai.core.runner import run_case

    # Use the same case directory for replay (scripts already generated)
    explore_case_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "baidu_search"
    replay_case_dir = explore_case_dir  # Same directory — scripts exist from explore
    explore_scripts_dir = explore_case_dir / "scripts"
    replay_scripts_dir = replay_case_dir / "scripts"

    # First generate scripts with explore mode if needed
    if not explore_scripts_dir.exists() or not list(explore_scripts_dir.glob("*.py")):
        print("  Generating scripts with explore mode first...")
        await run_case(explore_case_dir)

    # Copy scripts to replay case directory
    if replay_scripts_dir.exists():
        for f in replay_scripts_dir.glob("*.py"):
            f.unlink()
    else:
        replay_scripts_dir.mkdir(parents=True, exist_ok=True)

    for f in explore_scripts_dir.glob("*.py"):
        (replay_scripts_dir / f.name).write_text(f.read_text())

    print(f"  Copied {len(list(replay_scripts_dir.glob('*.py')))} scripts to replay case")

    # Run in replay mode (scripts already exist)
    print("  Running replay mode (directly executing scripts)...")
    start = time.time()
    report = await run_case(replay_case_dir)
    replay_time = time.time() - start

    print(f"  Time: {replay_time:.2f}s")
    print(f"  Status: {report['status']}")
    print(f"  Steps: {report['success_count']}/{report['total_steps']}")

    # Verify all steps used replay mode
    all_replay = all(s['mode'] == 'replay' for s in report['steps'])
    print(f"  All replay mode: {all_replay}")

    # Collect report data
    report_data["replay"]["time"] = replay_time
    report_data["replay"]["status"] = "PASS" if report['status'] == 'completed' and all_replay else "FAIL"
    report_data["replay"]["steps"] = report.get("steps", [])
    report_data["replay"]["all_replay"] = all_replay

    success = report['status'] == 'completed' and all_replay
    print(f"  {'PASS' if success else 'FAIL'}\n")
    return replay_time, success


def generate_html_report():
    """Generate HTML test report."""
    report_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    explore_time = report_data["explore"]["time"]
    replay_time = report_data["replay"]["time"]
    speedup = explore_time / replay_time if replay_time > 0 else 0
    time_saved = explore_time - replay_time

    report_data["comparison"]["speedup"] = speedup
    report_data["comparison"]["time_saved"] = time_saved

    # Generate step rows for explore
    explore_steps_html = ""
    for step in report_data["explore"]["steps"]:
        status_class = "success" if step.get("status") == "success" else "failed"
        explore_steps_html += f"""
        <tr>
            <td>{step.get('step_id', 'N/A')}</td>
            <td><span class="badge {status_class}">{step.get('status', 'N/A')}</span></td>
            <td><span class="badge explore">{step.get('mode', 'N/A')}</span></td>
            <td>{step.get('summary', 'N/A')[:50]}...</td>
        </tr>"""

    # Generate step rows for replay
    replay_steps_html = ""
    for step in report_data["replay"]["steps"]:
        status_class = "success" if step.get("status") == "success" else "failed"
        replay_steps_html += f"""
        <tr>
            <td>{step.get('step_id', 'N/A')}</td>
            <td><span class="badge {status_class}">{step.get('status', 'N/A')}</span></td>
            <td><span class="badge replay">{step.get('mode', 'N/A')}</span></td>
            <td>{step.get('summary', 'N/A')[:50]}...</td>
        </tr>"""

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skiritai 探索模式 vs 回放模式 对比报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .timestamp {{ opacity: 0.8; font-size: 14px; }}
        .card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .card h2 {{ color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; color: #2c3e50; }}
        .stat-card .label {{ color: #666; margin-top: 5px; font-size: 14px; }}
        .comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .mode-card {{ padding: 20px; border-radius: 8px; }}
        .mode-card.explore {{ background: #e3f2fd; border-left: 4px solid #2196f3; }}
        .mode-card.replay {{ background: #e8f5e9; border-left: 4px solid #4caf50; }}
        .mode-card h3 {{ margin-bottom: 15px; }}
        .mode-card .time {{ font-size: 24px; font-weight: bold; }}
        .mode-card.explore .time {{ color: #1976d2; }}
        .mode-card.replay .time {{ color: #388e3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .badge.success {{ background: #e8f5e9; color: #2e7d32; }}
        .badge.failed {{ background: #ffebee; color: #c62828; }}
        .badge.explore {{ background: #e3f2fd; color: #1565c0; }}
        .badge.replay {{ background: #e8f5e9; color: #2e7d32; }}
        .speedup {{ background: #2c3e50; color: white; padding: 30px; border-radius: 10px; text-align: center; }}
        .speedup .value {{ font-size: 48px; font-weight: bold; }}
        .speedup .label {{ font-size: 18px; opacity: 0.9; }}
        .behavior-list {{ list-style: none; padding: 0; }}
        .behavior-list li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .behavior-list li:before {{ content: "✓"; color: #4caf50; margin-right: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Skiritai 探索模式 vs 回放模式 对比报告</h1>
            <div class="timestamp">生成时间: {report_data['timestamp']}</div>
        </div>

        <div class="card">
            <h2>总体对比</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="value">{explore_time:.2f}s</div>
                    <div class="label">探索模式耗时</div>
                </div>
                <div class="stat-card">
                    <div class="value">{replay_time:.2f}s</div>
                    <div class="label">回放模式耗时</div>
                </div>
                <div class="stat-card">
                    <div class="value">{speedup:.1f}x</div>
                    <div class="label">加速比</div>
                </div>
                <div class="stat-card">
                    <div class="value">{time_saved:.2f}s</div>
                    <div class="label">节省时间</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>模式详情</h2>
            <div class="comparison">
                <div class="mode-card explore">
                    <h3>探索模式 (Explore)</h3>
                    <div class="time">{explore_time:.2f}s</div>
                    <p style="margin-top: 10px; color: #666;">状态: <span class="badge {report_data['explore']['status']}">{report_data['explore']['status']}</span></p>
                    <p style="margin-top: 5px; color: #666;">生成脚本: {report_data['explore']['scripts_generated']} 个</p>
                    <h4 style="margin-top: 15px; margin-bottom: 10px;">行为:</h4>
                    <ul class="behavior-list">
                        <li>调用 AI 推理分析页面</li>
                        <li>AI 自主决定工具调用</li>
                        <li>生成回放脚本</li>
                        <li>每次重新探索</li>
                    </ul>
                </div>
                <div class="mode-card replay">
                    <h3>回放模式 (Replay)</h3>
                    <div class="time">{replay_time:.2f}s</div>
                    <p style="margin-top: 10px; color: #666;">状态: <span class="badge {report_data['replay']['status']}">{report_data['replay']['status']}</span></p>
                    <p style="margin-top: 5px; color: #666;">回放模式: {report_data['replay']['all_replay']}</p>
                    <h4 style="margin-top: 15px; margin-bottom: 10px;">行为:</h4>
                    <ul class="behavior-list">
                        <li>AI 判断有回放脚本</li>
                        <li>AI 直接执行脚本</li>
                        <li>快速稳定执行</li>
                        <li>复用已有脚本</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>探索模式执行详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>步骤</th>
                        <th>状态</th>
                        <th>模式</th>
                        <th>摘要</th>
                    </tr>
                </thead>
                <tbody>
                    {explore_steps_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>回放模式执行详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>步骤</th>
                        <th>状态</th>
                        <th>模式</th>
                        <th>摘要</th>
                    </tr>
                </thead>
                <tbody>
                    {replay_steps_html}
                </tbody>
            </table>
        </div>

        <div class="speedup">
            <div class="value">{speedup:.1f}x</div>
            <div class="label">回放模式比探索模式快</div>
        </div>
    </div>
</body>
</html>
"""
    return html


async def test_comparison():
    """Test: compare explore vs replay performance."""
    print("=== Test: Explore vs Replay Comparison ===\n")

    # First run: explore mode (generates scripts)
    explore_time, explore_ok = await test_explore_generates_scripts()

    # Second run: replay mode (uses scripts)
    replay_time, replay_ok = await test_replay_executes_scripts()

    # Summary
    print("=== Comparison Summary ===")
    print(f"  Explore mode: {explore_time:.2f}s {'(PASS)' if explore_ok else '(FAIL)'}")
    print(f"  Replay mode:  {replay_time:.2f}s {'(PASS)' if replay_ok else '(FAIL)'}")

    if explore_ok and replay_ok:
        speedup = explore_time / replay_time if replay_time > 0 else float('inf')
        print(f"  Speedup: {speedup:.1f}x faster with replay")
        print(f"  Time saved: {explore_time - replay_time:.2f}s")

        # Verify replay is faster
        is_faster = replay_time < explore_time
        print(f"  Replay is faster: {is_faster}")
        print(f"  {'PASS' if is_faster else 'FAIL'}\n")

        # Generate HTML report
        html = generate_html_report()
        report_path = Path(__file__).resolve().parent.parent.parent / "test_report.html"
        report_path.write_text(html, encoding="utf-8")
        print(f"  Report generated: {report_path}")

        return is_faster
    else:
        print("  SKIP: Cannot compare (one or both modes failed)\n")
        return False


async def main():
    print("Replay vs Explore test suite\n")
    result = await test_comparison()
    print(f"Overall: {'PASS' if result else 'FAIL'}")


if __name__ == "__main__":
    asyncio.run(main())
