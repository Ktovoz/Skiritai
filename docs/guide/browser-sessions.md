# Browser Sessions

Skiritai supports two browser modes: **standard** (in-process) and **persistent** (CDP-based, survives Python restarts).

## Standard Mode

The default mode. The browser runs as part of the Python process and is destroyed when the process exits.

```python
class MyTest(BaseCase):
    async def setup(self):
        await self.launch_browser()   # Default: standard mode

    async def teardown(self):
        await self.close_browser()
```

## Persistent Mode

The browser launches as an **independent subprocess** via Chrome DevTools Protocol (CDP). It survives Python restarts, crashes, and disconnections. You can disconnect and reconnect at will.

```python
class MyTest(BaseCase):
    async def setup(self):
        await self.launch_browser_persistent()  # CDP subprocess

    async def teardown(self):
        await self.disconnect_browser()         # Detach, browser stays alive
```

### Key Benefits

- **Survives restarts** — The browser process outlives your Python scripts
- **Cross-process reconnection** — Launch in one process, reconnect from another
- **State preserved** — Pages, cookies, local storage persist between connections
- **CI-friendly cleanup** — `atexit` handler kills orphan processes on normal exit

## CDP Architecture

```
Python Process          Browser Subprocess
┌──────────┐     CDP     ┌──────────────┐
│ Playwright │ ←────────→ │  Chromium    │
│  (PW)     │  ws://     │  --remote-   │
│   + CDP   │            │  debugging-  │
│  client   │            │  port=9222   │
└──────────┘            └──────────────┘
         │                      │
         .browser_session       Session file persists
         (cdp_port + pid)       on disk
```

The session file `.browser_session` stores the CDP port and process PID so it can be found by another Python process.

## Lifecycle API

### Full Control

```python
# Setup (first run)
await self.launch_browser_persistent()   # Start Chromium subprocess
# ... run steps ...

# Disconnect (keep browser alive)
await self.disconnect_browser()          # Python exits, browser stays

# Reconnect (later, possibly in a different script)
await self.reconnect_browser()           # Reattach via persisted CDP port
# ... run more steps ...

# Teardown (final)
await self.terminate_browser()           # Kill browser, clean up session
```

### Standard Mode (non-persistent)

```python
await self.launch_browser()              # In-process browser
await self.close_browser()               # Kill browser
```

## Session Management (CLI)

```bash
# Check if a persistent browser is running for a case
skiritai browser status <case_dir>

# Kill the persistent browser and clean up the session file
skiritai browser cleanup <case_dir>
```

## Session File

Saved at `<case_dir>/.browser_session`:

```json
{
  "cdp_port": 9222,
  "pid": 48291
}
```

## Programmatic Checks

```python
# Check if a session file exists
self.has_browser_session()    # True if .browser_session exists

# Check if the browser process is alive
from skiritai.core.browser import is_browser_alive
is_browser_alive(case_dir)

# Load session info
from skiritai.core.browser import load_session
session = load_session(case_dir)  # {"cdp_port": 9222, "pid": 48291}
```

## CI / Headless

Set environment variables for CI mode:

```bash
SKIRITAI_HEADLESS=true       # Headless mode
CI=true                      # Adds --no-sandbox flag
SKIRITAI_CHROME_PATH=/path   # Custom Chromium binary
```
