"""Skiritai CLI — command-line interface for the test automation framework.

Usage:
    skiritai run <case_dir>          Run a test case
    skiritai serve [--host] [--port]  Start the web server (requires [web] extra)
    skiritai list [cases_root]        List available test cases
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="skiritai",
        description="Skiritai — AI-driven browser test automation framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Run a test case")
    run_parser.add_argument("case_dir", type=str, help="Path to case directory containing case.py")

    # --- serve ---
    serve_parser = subparsers.add_parser("serve", help="Start the web server (requires [web] extra)")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    serve_parser.add_argument("--cases-root", type=str, default=None,
                              help="Root directory for case discovery (default: SKIRITAI_CASES_ROOT or ./cases)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="List available test cases")
    list_parser.add_argument("cases_root", type=str, nargs="?", default="examples",
                             help="Root directory containing case folders (default: examples)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "serve":
        _cmd_serve(args)
    elif args.command == "list":
        _cmd_list(args)


def _cmd_run(args):
    """Run a test case."""
    from skiritai.core.agent_loop import register_all_tools
    register_all_tools()

    from skiritai.core.runner import run_case

    case_dir = Path(args.case_dir).resolve()
    if not case_dir.exists():
        print(f"Error: case directory not found: {case_dir}")
        sys.exit(1)

    report = asyncio.run(run_case(case_dir))

    # Print report
    print(f"\n{'='*60}")
    print(f"Case: {report.get('case_name')}")
    print(f"Status: {report.get('status')}")
    print(f"Steps: {report.get('success_count', 0)}/{report.get('total_steps', 0)} passed")
    if report.get("elapsed_seconds"):
        print(f"Elapsed: {report['elapsed_seconds']}s")
    print(f"{'='*60}")

    for step in report.get("steps", []):
        icon = "✓" if step["status"] == "success" else "✗"
        print(f"  {icon} {step['step_id']} ({step.get('mode', '')}) — {step.get('summary', '')}")

    sys.exit(0 if report.get("status") == "completed" else 1)


def _cmd_serve(args):
    """Start the web server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required for the serve command.")
        print("Install with: pip install skiritai[web]")
        sys.exit(1)

    # Set cases root via env var so the factory picks it up
    if args.cases_root:
        os.environ["SKIRITAI_CASES_ROOT"] = str(Path(args.cases_root).resolve())

    uvicorn.run(
        "skiritai.web.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


def _cmd_list(args):
    """List available test cases."""
    from skiritai.core.runner import list_cases

    cases_root = Path(args.cases_root).resolve()
    cases = list_cases(cases_root)

    if not cases:
        print(f"No cases found in {cases_root}")
        return

    print(f"Found {len(cases)} case(s) in {cases_root}:\n")
    for c in cases:
        print(f"  {c['id']}")
        print(f"    Class: {c['name']}")
        print(f"    Steps: {', '.join(c['steps']) or '(none)'}")
        print()


if __name__ == "__main__":
    main()
