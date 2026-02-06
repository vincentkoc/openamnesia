# OpenAmnesia

Local-first ingestion service that converts tool/session exhaust into normalized events, sessions, moments, and skill candidates.

## What is implemented (v0 ingestion scaffold)
- Python daemon service (`amnesia_daemon.py`) with `--once` and watch-loop modes
- Source connectors with a shared interface
  - `cursor` (file-drop `.jsonl`)
  - `codex` (file-drop `.jsonl`)
  - `terminal` (file-drop `.log`)
- Hookable pipeline stages
  - normalize -> sessionize -> momentize -> extract -> skill_mine -> optimize
  - extension hooks available before/after major stages
- Swappable store backend via config
  - `sqlite` (default)
  - `memory` (dev/testing)
- SQLite schema for raw and derived objects in `amnesia/store/schema.sql`

## Project layout
- `amnesia_daemon.py`: daemon entrypoint and orchestration
- `amnesia/config.py`: typed config loading + default config generation
- `amnesia/connectors/`: source connectors and connector registry
- `amnesia/pipeline/`: ingestion pipeline primitives and hook registry
- `amnesia/store/`: DB abstraction + backend implementations

## Quick start
1. Create env and install:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. (Optional) write default config:
```bash
amnesia-daemon --init-config --config config.yaml
```

3. Run one pass:
```bash
amnesia-daemon --config config.yaml --once
```

4. Run in watch mode:
```bash
amnesia-daemon --config config.yaml
```

Default SQLite file path in `config.yaml`: `./data/amnesia.db`

## Config snippet
```yaml
store:
  backend: sqlite   # or memory
  dsn: sqlite:///./data/amnesia.db

daemon:
  poll_interval_seconds: 5
  state_path: ./.amnesia_state.yaml
```

## Hooking pipeline stages
`Daemon` exposes `self.hooks` (`HookRegistry`). Each hook receives and returns `PipelineContext`:
- `pre_normalize`
- `post_normalize`
- `post_sessionize`
- `post_momentize`
- `post_extract`
- `post_skill_mine`

This gives you clean extension points for redaction, enrichment, custom segmentation, and skill promotion logic.
