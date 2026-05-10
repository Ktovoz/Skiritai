"""Test Python-based case runner."""
import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


async def test_discover_case():
    """Test: discover case class from Python file."""
    print("=== Test: Discover Case Class ===")

    from skiritai.core.runner import discover_case_class

    case_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "baidu_search"
    case_class = discover_case_class(case_dir)

    print(f"  Class: {case_class.__name__}")

    # Create instance to get steps
    instance = case_class()
    steps = instance.get_step_methods()

    print(f"  Steps: {steps}")
    print(f"  PASS\n" if len(steps) > 0 else "  FAIL\n")
    return case_class


async def test_run_case():
    """Test: run a full Python-based case."""
    print("=== Test: Run Python Case ===")

    from skiritai.core.runner import run_case

    case_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "baidu_search"
    report = await run_case(case_dir)

    print(f"  Status: {report['status']}")
    print(f"  Results: {report['success_count']}/{report['total_steps']}")
    for step in report['steps']:
        print(f"    - {step['step_id']}: {step['status']} ({step['mode']})")

    print("  PASS\n" if report['status'] == 'completed' else "  FAIL\n")
    return report


async def test_replay_mode():
    """Test: replay mode with saved scripts."""
    print("=== Test: Replay Mode ===")

    from skiritai.core.runner import run_case

    case_dir = Path(__file__).resolve().parent.parent.parent / "examples" / "baidu_search"

    # Run first to generate scripts
    print("  First run (explore mode)...")
    report1 = await run_case(case_dir)
    print(f"  Status: {report1['status']}")

    if report1['status'] != 'completed':
        print("  SKIP: First run failed\n")
        return

    # Run again to test replay
    print("  Second run (replay mode)...")
    report2 = await run_case(case_dir)
    print(f"  Status: {report2['status']}")

    # Check that all steps used replay mode
    all_replay = all(s['mode'] == 'replay' for s in report2['steps'])
    print(f"  All replay: {all_replay}")

    print("  PASS\n" if report2['status'] == 'completed' and all_replay else "  FAIL\n")
    return report2


async def main():
    print("Python Case Runner test suite\n")
    await test_discover_case()
    await test_run_case()
    # await test_replay_mode()  # uncomment to test replay
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
