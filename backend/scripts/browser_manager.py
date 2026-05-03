#!/usr/bin/env python3
"""Browser session manager — check, list, and clean up leftover browser processes.

Usage:
    python scripts/browser_manager.py status    — Show all browser sessions
    python scripts/browser_manager.py cleanup    — Kill all leftover browsers
    python scripts/browser_manager.py cleanup <case_dir>  — Kill specific session
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path


def find_chrome_processes() -> list[dict]:
    """Find all Chrome/Chromium processes started with --remote-debugging-port."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,command"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return []

    processes = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if "--remote-debugging-port" not in line:
            continue
        if "Google Chrome" not in line and "chromium" not in line.lower():
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        pid = int(parts[0])
        cmd = parts[1]
        # Extract port
        port = None
        for part in cmd.split():
            if part.startswith("--remote-debugging-port="):
                port = part.split("=", 1)[1]
                break
        processes.append({"pid": pid, "port": port, "command": cmd[:120]})
    return processes


def find_session_files(root: Path) -> list[dict]:
    """Find all .browser_session files under the given root directory."""
    sessions = []
    for path in root.rglob(".browser_session"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cdp_port = data.get("cdp_port")
            pid = data.get("pid")

            # Check if the process is alive
            alive = False
            if pid:
                try:
                    os.kill(pid, 0)
                    alive = True
                except OSError:
                    pass

            sessions.append({
                "session_file": str(path),
                "case_dir": str(path.parent),
                "cdp_port": cdp_port,
                "pid": pid,
                "alive": alive,
            })
        except (json.JSONDecodeError, KeyError):
            sessions.append({
                "session_file": str(path),
                "case_dir": str(path.parent),
                "cdp_port": None,
                "pid": None,
                "alive": False,
                "error": "Corrupted session file",
            })
    return sessions


def kill_process(pid: int) -> bool:
    """Kill a process by PID. Returns True if successful."""
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False


def cleanup_session_file(path: Path) -> bool:
    """Remove a session file. Returns True if removed."""
    try:
        if path.exists():
            path.unlink()
            return True
    except Exception:
        pass
    return False


def cmd_status():
    """Show all browser sessions and Chrome processes."""
    print("=" * 60)
    print("Browser Session Status")
    print("=" * 60)

    # 1. Check Chrome processes
    chrome_procs = find_chrome_processes()
    print(f"\nChrome processes with --remote-debugging-port: {len(chrome_procs)}")
    if chrome_procs:
        for p in chrome_procs:
            status = "ALIVE" if True else "DEAD"
            print(f"  PID {p['pid']:>6}  port={p['port'] or '?':>5}  {status}")
    else:
        print("  (none)")

    # 2. Check session files
    project_root = Path(__file__).resolve().parent.parent.parent
    cases_dir = project_root / "cases"
    tmp_dir = Path("/tmp")

    sessions = []
    if cases_dir.exists():
        sessions.extend(find_session_files(cases_dir))
    sessions.extend(find_session_files(tmp_dir))

    # Also check temp directories
    import tempfile
    tmp_base = Path(tempfile.gettempdir())
    sessions.extend(find_session_files(tmp_base))
    # Deduplicate
    seen = set()
    unique_sessions = []
    for s in sessions:
        if s["session_file"] not in seen:
            seen.add(s["session_file"])
            unique_sessions.append(s)
    sessions = unique_sessions

    print(f"\nSession files found: {len(sessions)}")
    if sessions:
        for s in sessions:
            status = "ALIVE" if s["alive"] else "DEAD"
            print(f"  PID {s.get('pid', '?'):>6}  port={s.get('cdp_port', '?'):>5}  {status}")
            print(f"    file: {s['session_file']}")
    else:
        print("  (none)")

    # 3. Summary
    alive_count = sum(1 for p in chrome_procs) + sum(1 for s in sessions if s["alive"])
    dead_sessions = [s for s in sessions if not s["alive"]]

    print(f"\nSummary:")
    print(f"  Active Chrome processes: {len(chrome_procs)}")
    print(f"  Alive sessions: {sum(1 for s in sessions if s['alive'])}")
    print(f"  Stale sessions (files without live process): {len(dead_sessions)}")

    if dead_sessions:
        print(f"\n  Run 'python scripts/browser_manager.py cleanup' to remove stale sessions.")


def cmd_cleanup(specific_case_dir: str | None = None):
    """Kill leftover browsers and clean up session files."""
    print("=" * 60)
    print("Browser Cleanup")
    print("=" * 60)

    killed = 0
    cleaned = 0

    # 1. Kill Chrome debug processes
    chrome_procs = find_chrome_processes()
    if chrome_procs:
        print(f"\nFound {len(chrome_procs)} Chrome debug process(es):")
        for p in chrome_procs:
            pid = p["pid"]
            if kill_process(pid):
                print(f"  Killed PID {pid} (port={p['port']})")
                killed += 1
            else:
                print(f"  PID {pid} already dead")
    else:
        print("\nNo Chrome debug processes found.")

    # 2. Clean up session files
    search_dirs = [Path("/tmp")]
    project_root = Path(__file__).resolve().parent.parent.parent
    cases_dir = project_root / "cases"
    if cases_dir.exists():
        search_dirs.append(cases_dir)

    import tempfile
    search_dirs.append(Path(tempfile.gettempdir()))

    for search_dir in search_dirs:
        for path in search_dir.rglob(".browser_session"):
            if specific_case_dir and str(path.parent) != specific_case_dir:
                continue
            if cleanup_session_file(path):
                print(f"  Removed: {path}")
                cleaned += 1

    print(f"\nDone: killed {killed} process(es), cleaned {cleaned} session file(s).")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "cleanup":
        specific = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_cleanup(specific)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
