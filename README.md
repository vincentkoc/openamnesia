# OpenAmnesia

Local-first ingestion service that converts tool/session exhaust into normalized events, sessions, moments, and skill candidates.

## Scope completed for ingestion phase
- Python daemon service (`amnesia_daemon.py`) with `--once` and watch-loop modes
- Source connectors with shared interface:
  - `cursor` (`.jsonl` file-drop)
  - `codex` (`.jsonl` file-drop)
  - `terminal` (`.log` file-drop)
- Source operational status tracking (`idle`, `ingesting`, `error`) persisted in DB
- Hookable pipeline stages:
  - normalize -> sessionize -> momentize -> extract -> skill_mine -> optimize
- Config-driven plugin loading for hooks (`module.path:function_name`)
- Swappable store backend via config:
  - `sqlite` (default)
  - `memory` (dev/testing)
- SQLite persistence includes:
  - core entities: `events`, `sessions`, `moments`, `skills`
  - operational entities: `source_status`, `ingest_audit`, `exports`
- Optional exports:
  - daily notes markdown (`exports/daily/YYYY_MM_DD.md`)
  - skill YAML files (`exports/skills/*.yaml`)

## Project layout
- `amnesia_daemon.py`: daemon entrypoint + orchestration
- `amnesia/config.py`: typed config and defaults
- `amnesia/connectors/`: source connectors and registry
- `amnesia/pipeline/`: processing stages, hooks, plugin loader
- `amnesia/store/`: store interface + sqlite/memory implementations
- `amnesia/exports/`: markdown and YAML exporters
- `tests/`: ingestion-focused tests

## Quick start
1. Create env and install:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

2. Run one ingestion pass:
```bash
amnesia-daemon --config config.yaml --once
```

3. Run continuous watch mode:
```bash
amnesia-daemon --config config.yaml
```

4. Show source statuses:
```bash
amnesia-daemon --config config.yaml --sources
```

5. Generate default config if needed:
```bash
amnesia-daemon --init-config --config config.yaml
```

## Config
```yaml
store:
  backend: sqlite   # sqlite | memory
  dsn: sqlite:///./data/amnesia.db

daemon:
  poll_interval_seconds: 5
  state_path: ./.amnesia_state.yaml

exports:
  enabled: true
  daily_dir: ./exports/daily
  skills_dir: ./exports/skills

hooks:
  plugins: []
```

## Hook plugins
Each plugin path must resolve to a function that receives `HookRegistry` and registers hooks.

Example config:
```yaml
hooks:
  plugins:
    - my_project.amnesia_plugins:register_hooks
```

Example plugin:
```python
from amnesia.pipeline.hooks import HookRegistry

def register_hooks(registry: HookRegistry) -> None:
    def redact(ctx):
        for event in ctx.events:
            event.content = event.content.replace("SECRET", "[REDACTED]")
        return ctx

    registry.post_normalize.append(redact)
```

## Validate
```bash
pytest -q
python -m mypy --config-file pyproject.toml
```
