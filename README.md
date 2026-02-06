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
- Rich terminal display for run summaries and source status tables
- Internal source event bus (`amnesia/internal/events.py`) for runtime observability
- Source-level filtering hooks (`include_contains`, `exclude_contains`)
- Source poll stats propagated to summaries (`items`, `groups`, filtered counts)
- iMessage source connector (`imessage` JSONL export ingestion)
- Source-by-source test helper (`scripts/test_source.py`)

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

5. Test one source in isolation:
```bash
python scripts/test_source.py --config config.yaml --source imessage
```

6. Inspect recent internal events:
```bash
amnesia-daemon --config config.yaml --once --events-limit 20
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

logging:
  level: INFO
```

Source filter config example:
```yaml
sources:
  - name: imessage
    enabled: true
    path: ./ingest/imessage
    pattern: "*.jsonl"
    include_contains: ["dinner", "plan"]
    exclude_contains: ["spam"]
    include_groups: ["lauren", "family"]
    exclude_groups: ["otp", "bank"]
    include_actors: ["me", "contact"]
    exclude_actors: ["system"]
    since_ts: "2025-04-01T00:00:00Z"
    until_ts: "2025-04-30T23:59:59Z"
```

Universal filter dimensions:
- content: `include_contains` / `exclude_contains`
- group/chat: `include_groups` / `exclude_groups`
- actor: `include_actors` / `exclude_actors`
- time window: `since_ts` / `until_ts` (ISO-8601)

`scripts/test_source.py` supports CLI overrides:
```bash
python scripts/test_source.py --config config.yaml --source imessage \
  --include-group lauren --exclude-group otp \
  --include-actor contact --since 2025-04-01T00:00:00Z --until 2025-04-10T00:00:00Z
```

## Source helper script
- `scripts/test_source.py` runs a single connector and persists connector state offsets.
- Default state path: `./.amnesia_source_test_state.yaml`
- Useful flags:
  - `--sample 10` show more sample records
  - `--json` machine-readable output
  - `--no-save-state` dry-run polling without offset updates
  - `--reset-state` re-read source from the beginning for test runs

## Source module template (enforced)
Each source now follows this normalized shape:
- `amnesia/sources/{source}/{source}.py`
- `amnesia/sources/{source}/helpers.py`
- `amnesia/sources/{source}/reporting.py`
- `amnesia/sources/{source}/types.py`
- `amnesia/sources/{source}/ops/{operation}_ops.py`

At runtime, module structure is validated via `amnesia/sources/registry.py`.

## iMessage SQLite mode
`imessage` defaults to reading macOS Messages DB:
- `options.mode: sqlite`
- `options.db_path: ~/Library/Messages/chat.db`
- state key: `last_rowid` (incremental ingestion)

Fallback mode remains available for local test files:
```yaml
sources:
  - name: imessage
    options:
      mode: jsonl
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
