"""Skiritai CLI — command-line interface for the test automation framework.

Usage:
    skiritai run <case_dir>          Run a test case
    skiritai serve [--host] [--port]  Start the web server (requires [web] extra)
    skiritai list [cases_root]        List available test cases
    skiritai config show              Display current effective LLM config
    skiritai config check             Verify LLM config by making a test call
    skiritai config init              Generate a skiritai.toml template
    skiritai browser status [dir]     Check persistent browser session status
    skiritai browser cleanup [dir]    Kill orphan browser and remove session file
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
    run_parser.add_argument("--results-dir", type=str, default=None,
                            help="Directory to save test results (default: <case_dir>/test_results)")
    run_parser.add_argument("--env-file", type=str, default=None,
                            help="Path to .env file to load before running")
    run_parser.add_argument("--config", type=str, default=None,
                            help="Path to skiritai.toml or skiritai.yaml config file")
    run_parser.add_argument("--llm", type=str, default=None,
                            help="LLM provider name (openai, anthropic)")
    run_parser.add_argument("--api-key", type=str, default=None,
                            help="LLM API key")
    run_parser.add_argument("--model", type=str, default=None,
                            help="LLM model name")

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

    # --- config ---
    config_parser = subparsers.add_parser("config", help="LLM configuration diagnostics")
    config_sub = config_parser.add_subparsers(dest="config_command", help="Config commands")
    config_sub.add_parser("show", help="Display current effective LLM configuration")
    config_sub.add_parser("check", help="Verify LLM config by making a test call")
    config_sub.add_parser("init", help="Generate a skiritai.toml template in current directory")

    # --- browser ---
    browser_parser = subparsers.add_parser("browser", help="Manage persistent browser sessions")
    browser_sub = browser_parser.add_subparsers(dest="browser_command", help="Browser commands")
    status_parser = browser_sub.add_parser("status", help="Check browser session status")
    status_parser.add_argument("case_dir", type=str, nargs="?", default=".",
                               help="Case directory with .browser_session file (default: current dir)")
    cleanup_parser = browser_sub.add_parser("cleanup", help="Kill orphan browser and remove session file")
    cleanup_parser.add_argument("case_dir", type=str, nargs="?", default=".",
                                help="Case directory with .browser_session file (default: current dir)")

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
    elif args.command == "config":
        _cmd_config(args)
    elif args.command == "browser":
        _cmd_browser(args)


def _cmd_run(args):
    """Run a test case (Python or YAML, auto-detected).

    Detection priority when both case.py and case.yaml exist: Python wins.
    Use ``run_yaml_case()`` in Python code to explicitly run a YAML case.
    """
    from skiritai.llm._factory import load_env, create_llm

    # 1. Load .env if specified
    if getattr(args, "env_file", None):
        load_env(args.env_file)

    # 2. Create provider from CLI args if any LLM-related args given
    llm = None
    if getattr(args, "llm", None) or getattr(args, "api_key", None) or getattr(args, "model", None) or getattr(args, "config", None):
        llm = create_llm(
            provider=getattr(args, "llm", None),
            api_key=getattr(args, "api_key", None),
            model=getattr(args, "model", None),
            from_file=getattr(args, "config", None),
        )

    from skiritai.core.agent_loop import register_all_tools
    register_all_tools()

    case_dir = Path(args.case_dir).resolve()
    if not case_dir.exists():
        print(f"Error: case directory not found: {case_dir}")
        sys.exit(1)

    results_dir = Path(args.results_dir).resolve() if args.results_dir else None

    # Detection priority: case.py > case.yaml/case.yml.
    # When both exist, Python is preferred. Use run_yaml_case() to force YAML.
    has_yaml = (case_dir / "case.yaml").is_file() or (case_dir / "case.yml").is_file()
    has_py = (case_dir / "case.py").is_file()

    if has_yaml and not has_py:
        from skiritai.core.yaml_runner import run_yaml_case
        report = asyncio.run(run_yaml_case(case_dir, results_dir=results_dir, llm=llm))
    else:
        from skiritai.core.runner import run_case
        report = asyncio.run(run_case(case_dir, results_dir=results_dir, llm=llm))

    # Print report
    print(f"\n{'=' * 60}")
    print(f"Case: {report.get('case_name')}")
    print(f"Status: {report.get('status')}")
    print(f"Steps: {report.get('success_count', 0)}/{report.get('total_steps', 0)} passed")
    if report.get("elapsed_seconds"):
        print(f"Elapsed: {report['elapsed_seconds']}s")
    print(f"{'=' * 60}")

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
        source = c.get("source", "python")
        tag = " [yaml]" if source == "yaml" else ""
        print(f"  {c['id']}{tag}")
        print(f"    Name:  {c['name']}")
        steps = c.get("steps", [])
        if steps and isinstance(steps, list):
            if isinstance(steps[0], str):
                print(f"    Steps: {', '.join(steps)}")
            elif isinstance(steps[0], dict):
                step_summaries = []
                for s in steps:
                    for key in ("action", "verify", "screenshot", "analyze", "page_info"):
                        if key in s:
                            step_summaries.append(f"{key}: {s[key]}")
                            break
                print(f"    Steps: {'; '.join(step_summaries)}")
            else:
                print(f"    Steps: {len(steps)} defined")
        else:
            print(f"    Steps: (none)")
        print()


def _cmd_config(args):
    """Handle config subcommand (show / check / init)."""
    if not getattr(args, "config_command", None):
        print("Usage: skiritai config {show|check|init}")
        sys.exit(1)

    if args.config_command == "show":
        _config_show()
    elif args.config_command == "check":
        _config_check()
    elif args.config_command == "init":
        _config_init()


def _config_show():
    """Display current effective LLM configuration."""
    from skiritai.llm._factory import create_llm, _load_config_file, _discover_config_file

    # Try to load config without building a provider
    import os
    from skiritai.llm._config import LLMConfig

    cfg = LLMConfig()
    cfg.provider = os.getenv("LLM_PROVIDER")
    cfg.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    cfg.base_url = os.getenv("OPENAI_BASE_URL")
    cfg.model = os.getenv("LLM_MODEL")

    file_cfg = _load_config_file(None)
    if file_cfg:
        for field in ("provider", "api_key", "base_url", "model", "temperature", "max_tokens"):
            val = getattr(file_cfg, field)
            if val is not None:
                setattr(cfg, field, val)

    config_file = _discover_config_file()

    print("Effective LLM Configuration:")
    print(f"  Config file: {config_file or '(none)'}")
    print(f"  Provider:    {cfg.provider or '(auto-detect)'}")
    print(f"  API key:     {_mask_key(cfg.api_key)}")
    print(f"  Base URL:    {cfg.base_url or '(default)'}")
    print(f"  Model:       {cfg.model or '(default)'}")
    print(f"  Temperature: {cfg.temperature or '(default)'}")
    print(f"  Max tokens:  {cfg.max_tokens or '(default)'}")


def _config_check():
    """Verify LLM config by attempting to create and build a provider."""
    from skiritai.llm._factory import create_llm

    try:
        provider = create_llm()
        print(f"Provider: {provider.name}")
        print("Configuration is valid.")
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)


def _config_init():
    """Generate a skiritai.toml template in current directory."""
    target = Path.cwd() / "skiritai.toml"
    if target.exists():
        print(f"skiritai.toml already exists in {Path.cwd()}")
        sys.exit(1)

    template = """\
[llm]
# LLM provider: "openai" or "anthropic" (omit for auto-detect)
# provider = "openai"

# API key (supports ${VAR} env var references)
# api_key = "${OPENAI_API_KEY}"

# Custom API base URL (optional, for proxy/custom endpoints)
# base_url = "https://api.openai.com/v1"

# Model name (omit for provider default)
# model = "gpt-4o"

# Generation parameters (optional)
# temperature = 0.2
# max_tokens = 4096
"""
    target.write_text(template, encoding="utf-8")
    print(f"Created {target}")
    print("Edit the file to configure your LLM provider.")


def _mask_key(key: str | None) -> str:
    """Mask an API key for display, showing first 4 and last 4 chars."""
    if not key:
        return "(not set)"
    if len(key) <= 12:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def _cmd_browser(args):
    """Manage persistent browser sessions."""
    from skiritai.core.browser import (
        has_persistent_session,
        is_browser_alive,
        load_session,
        kill_browser,
        cleanup_session,
    )

    if not args.browser_command:
        print("Usage: skiritai browser {status|cleanup} [case_dir]")
        sys.exit(1)

    case_dir = Path(args.case_dir).resolve()

    if args.browser_command == "status":
        if not has_persistent_session(case_dir):
            print(f"No browser session found in {case_dir}")
            return

        session = load_session(case_dir)
        if not session:
            print(f"Session file exists but is corrupted in {case_dir}")
            return

        alive = is_browser_alive(case_dir)
        print(f"Session file: {case_dir}/.browser_session")
        print(f"  CDP port: {session.get('cdp_port')}")
        print(f"  PID:      {session.get('pid')}")
        print(f"  Status:   {'alive' if alive else 'DEAD (orphan process)'}")

        if alive:
            print(f"\n  Connect: http://127.0.0.1:{session.get('cdp_port')}")
        else:
            print(f"\n  Run 'skiritai browser cleanup {case_dir}' to remove stale session.")

    elif args.browser_command == "cleanup":
        if not has_persistent_session(case_dir):
            print(f"No browser session found in {case_dir}")
            return

        killed = kill_browser(case_dir)
        if killed:
            print(f"Browser process killed and session file removed for {case_dir}")
        else:
            cleanup_session(case_dir)
            print(f"No live process found; stale session file removed for {case_dir}")


if __name__ == "__main__":
    main()
