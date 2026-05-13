# YAML Cases

Define test cases entirely in YAML — no Python code needed. The AI agent executes each step just like it would for a Python `BaseCase`.

## Basic Structure

```yaml
# case.yaml
name: My Search Test
headless: false
max_steps: 20
url: https://www.baidu.com
steps:
  - name: Search
    action: Search for "Playwright automation"

  - name: Verify
    verify: Search results are displayed

  - name: Screenshot
    screenshot: search_result
```

Place `case.yaml` (or `case.yml`) in a directory and run it with the CLI.

## Running YAML Cases

```bash
# Via CLI
skiritai run examples/beginner/baidu_search/03_yaml

# Via Python
from skiritai import run_yaml_case
from pathlib import Path
import asyncio

report = asyncio.run(run_yaml_case(Path("examples/beginner/baidu_search/03_yaml")))
```

## Step Types

| Step Key | Description | Required Argument |
|---|---|---|
| `action` | Natural language action → AI executes it | Action description string |
| `verify` | Natural language assertion → AI verifies (non-blocking on failure) | Assertion string |
| `screenshot` | Capture screenshot with given name | Screenshot name |
| `analyze` | Pre-analyze page DOM (injects context into next action) | (ignored) |
| `page_info` | Get page title, URL, text summary | (ignored) |

## Step-Level Options

Each step can specify an `on_failure` policy:

```yaml
steps:
  - action: Click the "Advanced Settings" link
    on_failure: skip    # Continue even if this step fails

  - action: Submit the form
    on_failure: abort   # Stop execution on failure (default)
```

| Policy | Behavior |
|---|---|
| `abort` (default) | Stop the entire case on failure |
| `skip` | Log warning and continue to the next step |

## Top-Level Fields

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | No | directory name | Display name for the case |
| `steps` | **Yes** | — | List of step definitions |
| `headless` | No | env or `false` | Run browser in headless mode |
| `max_steps` | No | `20` | Max agent tool-call steps per action |
| `url` | No | — | Navigate to this URL before running steps |

## Listing YAML Cases

```bash
skiritai list examples/
```

YAML cases are automatically discovered alongside Python cases. Each directory with a `case.yaml` or `case.yml` file is listed as a case.
