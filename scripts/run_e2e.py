#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from amnesia.config import load_config
from amnesia.exports.memory import MemoryExportConfig, export_memory_range
from amnesia.exports.skills_md import export_skills_md
from amnesia.sdk.imessage import IMessageIngestConfig, run_imessage_ingest
from amnesia.store.factory import build_store
from amnesia.utils.display.terminal import print_banner


@dataclass(slots=True)
class E2EConfig:
    mode: str = "recent"
    since_days: int = 7
    discovery_limit: int = 500
    log_level: str = "INFO"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAmnesia E2E demo runner")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--mode", choices=["recent", "all"], default=None)
    parser.add_argument("--since-days", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--log-level", default=None)
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--skip-discovery", action="store_true")
    parser.add_argument("--no-export-llm", action="store_true")
    return parser.parse_args()


def _load_e2e_config(path: Path) -> E2EConfig:
    if not path.exists():
        return E2EConfig()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    e2e_raw = raw.get("e2e", {}) or {}
    return E2EConfig(
        mode=str(e2e_raw.get("mode", "recent")),
        since_days=int(e2e_raw.get("since_days", 7)),
        discovery_limit=int(e2e_raw.get("discovery_limit", 500)),
        log_level=str(e2e_raw.get("log_level", "INFO")),
    )


def _resolve_sources(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    sources = []
    for item in raw.get("sources", []):
        if not item.get("enabled", True):
            continue
        name = item.get("name")
        if name:
            sources.append(str(name))
    return sources


def _run_imessage_if_enabled(config_path: Path, since_days: int, mode: str) -> int:
    cfg = load_config(config_path)
    source = next((item for item in cfg.sources if item.name == "imessage"), None)
    if source is None or not source.enabled:
        return 0
    mode_opt = str(source.options.get("mode", "sqlite")).lower()
    if mode_opt != "sqlite":
        return 0
    since = None
    if mode == "recent" and since_days > 0:
        since = (datetime.now(UTC) - timedelta(days=since_days)).isoformat(timespec="seconds")
    im_cfg = IMessageIngestConfig(
        db_path=str(
            Path(str(source.options.get("db_path", "~/Library/Messages/chat.db"))).expanduser()
        ),
        store_dsn=cfg.store.dsn,
        state_path=cfg.daemon.state_path,
        limit=int(source.options.get("limit", 5000)),
        entity_granularity="week",
        reset_state=True,
        save_state=True,
        since=since,
        until=source.until_ts,
        include_groups=source.include_groups,
        exclude_groups=source.exclude_groups,
        include_actors=source.include_actors,
        exclude_actors=source.exclude_actors,
        include_contains=source.include_contains,
        exclude_contains=source.exclude_contains,
    )
    result = run_imessage_ingest(im_cfg)
    print(
        f"iMessage ingest: seen={result.seen} ingested={result.ingested} "
        f"events={result.events} sessions={result.sessions} moments={result.moments}"
    )
    if result.error:
        print(f"iMessage ingest error: {result.error}")
        if result.hint:
            print(f"hint: {result.hint}")
        return 1
    return 0


def _reset_db(config_path: Path) -> None:
    cfg = load_config(config_path)
    dsn = cfg.store.dsn
    if not dsn.startswith("sqlite:///"):
        return
    db_path = Path(dsn.removeprefix("sqlite:///"))
    for suffix in ("", "-shm", "-wal"):
        target = Path(f"{db_path}{suffix}")
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass


def _since_arg(mode: str, since_days: int) -> list[str]:
    if mode == "all" or since_days <= 0:
        return []
    since_ts = (datetime.now(UTC) - timedelta(days=since_days)).isoformat(timespec="seconds")
    return ["--since", since_ts]


def _run(cmd: list[str], env: dict[str, str]) -> int:
    result = subprocess.run(cmd, env=env)
    return result.returncode


def _export_outputs(
    config_path: Path,
    *,
    since_days: int,
    mode: str,
    export_llm: bool,
    log_fn: Callable[[str], None] | None,
) -> tuple[list[Path], list[Path]]:
    cfg = load_config(config_path)
    if not cfg.exports.enabled:
        return [], []
    mem_paths: list[Path] = []
    if cfg.exports.memory.get("enabled", False):
        mem_cfg = MemoryExportConfig(**cfg.exports.memory)
        if not export_llm:
            mem_cfg.llm_enabled = False
        if mode == "recent" and since_days > 0:
            end_date = datetime.now(UTC).date()
            start_date = end_date - timedelta(days=max(0, since_days - 1))
            mem_paths = export_memory_range(
                dsn=cfg.store.dsn,
                cfg=mem_cfg,
                start_date=start_date,
                end_date=end_date,
                log_fn=log_fn,
            )
        else:
            end_date = datetime.now(UTC).date()
            start_date = end_date
            mem_paths = export_memory_range(
                dsn=cfg.store.dsn,
                cfg=mem_cfg,
                start_date=start_date,
                end_date=end_date,
                log_fn=log_fn,
            )
    store = build_store(cfg.store)
    skills = store.list_skills(limit=200)
    store.close()
    skill_paths: list[Path] = []
    if skills:
        skill_paths = export_skills_md(skills, out_dir=cfg.exports.skills_dir)
    return mem_paths, skill_paths


def _print_export_summary(
    console: Console, mem_paths: list[Path], skill_paths: list[Path]
) -> None:
    table = Table(title="Exports")
    table.add_column("Type")
    table.add_column("Count", justify="right")
    table.add_column("Sample")
    table.add_row("Memory", str(len(mem_paths)), ", ".join(map(str, mem_paths[:3])))
    table.add_row("Skills", str(len(skill_paths)), ", ".join(map(str, skill_paths[:3])))
    console.print(table)


def main() -> int:
    args = _parse_args()
    config_path = Path(args.config)
    cfg = _load_e2e_config(config_path)

    if args.mode:
        cfg.mode = args.mode
    if args.since_days is not None:
        cfg.since_days = args.since_days
    if args.limit is not None:
        cfg.discovery_limit = args.limit
    if args.log_level:
        cfg.log_level = args.log_level

    console = Console()
    print_banner()
    header = (
        f"mode={cfg.mode} since_days={cfg.since_days} "
        f"limit={cfg.discovery_limit} log_level={cfg.log_level}"
    )
    console.print(Panel(header, title="OpenAmnesia E2E", border_style="cyan"))

    if not args.skip_ingest and not args.skip_discovery:
        _reset_db(config_path)

    sources = _resolve_sources(config_path)
    if not sources:
        console.print("[bold red]No enabled sources in config.[/bold red]")
        return 2

    env = dict(os.environ)
    env["AMNESIA_BANNER_PRINTED"] = "1"
    env["AMNESIA_NO_BANNER"] = "1"
    env["AMNESIA_LOG_LEVEL"] = cfg.log_level

    stages = []
    if not args.skip_ingest:
        stages.append("ingest")
    if not args.skip_discovery:
        stages.extend([f"discover:{src}" for src in sources])
    since_args = _since_arg(cfg.mode, cfg.since_days)

    if stages:
        with Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[bold]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("start", total=max(1, len(stages)))
            if not args.skip_ingest:
                progress.update(task, description="ingest")
                if _run_imessage_if_enabled(config_path, cfg.since_days, cfg.mode) != 0:
                    console.print("[bold red]iMessage ingest failed.[/bold red]")
                    return 1
                ingest_cmd = [
                    "python",
                    "scripts/run_ingest.py",
                    "--config",
                    str(config_path),
                    "--reset-state",
                ] + since_args
                if _run(ingest_cmd, env) != 0:
                    console.print("[bold red]Ingest failed.[/bold red]")
                    return 1
                progress.advance(task, 1)

            if not args.skip_discovery:
                for src in sources:
                    progress.update(task, description=f"discover:{src}")
                    discover_cmd = [
                        "python",
                        "scripts/run_discovery.py",
                        "--source",
                        src,
                        "--limit",
                        str(cfg.discovery_limit),
                    ]
                    if cfg.mode == "recent" and cfg.since_days > 0:
                        discover_cmd += ["--since-days", str(cfg.since_days)]
                    if _run(discover_cmd, env) != 0:
                        console.print(f"[bold red]Discovery failed for {src}.[/bold red]")
                        return 1
                    progress.advance(task, 1)
    else:
        console.print("[bold cyan]Skipping ingest and discovery. Exporting only.[/bold cyan]")

    export_llm = not args.no_export_llm
    mem_paths, skill_paths = _export_outputs(
        config_path,
        since_days=cfg.since_days,
        mode=cfg.mode,
        export_llm=export_llm,
        log_fn=console.print,
    )
    if args.skip_ingest and args.skip_discovery:
        if not export_llm:
            console.print("[bold yellow]LLM summaries disabled for export-only run.[/bold yellow]")
        _print_export_summary(console, mem_paths, skill_paths)
    if mem_paths:
        console.print("[bold cyan]Memory exports:[/bold cyan]")
        for path in mem_paths:
            console.print(f"- {path}")
    if skill_paths:
        console.print("[bold cyan]Skill exports:[/bold cyan]")
        for path in skill_paths:
            console.print(f"- {path}")
    console.print("[bold green]E2E complete.[/bold green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
