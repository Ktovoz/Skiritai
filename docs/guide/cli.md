# CLI Commands

Skiritai provides a `skiritai` CLI with several subcommands.

## Run a Test Case

```bash
skiritai run <case_dir>
skiritai run . --case my_test.py
```

Works with Python `BaseCase` classes and [YAML cases](/guide/yaml-cases) (`case.yaml`). The runner auto-detects the case type.

Options:

- `--case` — Run a specific case file
- `cases_root` — Directory containing test cases

## Start the Web Server

```bash
skiritai serve
skiritai serve --host 0.0.0.0 --port 8080
```

## List Available Cases

```bash
skiritai list
skiritai list examples/
```

## Browser Session Management

```bash
# Check persistent browser status
skiritai browser status <case_dir>

# Kill orphan browser process
skiritai browser cleanup <case_dir>
```

The persistent browser mode keeps Chromium alive as a separate process (via CDP), so it survives Python restarts.
Session info is stored in `.browser_session`.
