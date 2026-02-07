#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


@dataclass(slots=True)
class E2EConfig:
    mode: str = "recent"
    since_days: int = 30
    discovery_limit: int = 500
    log_level: str = "INFO"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAmnesia E2E demo runner")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--mode", choices=["recent", "all"], default=None)
    parser.add_argument("--since-days", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--log-level", default=None)
    return parser.parse_args()


def _load_e2e_config(path: Path) -> E2EConfig:
    if not path.exists():
        return E2EConfig()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    e2e_raw = raw.get("e2e", {}) or {}
    return E2EConfig(
        mode=str(e2e_raw.get("mode", "recent")),
        since_days=int(e2e_raw.get("since_days", 30)),
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


def _since_arg(mode: str, since_days: int) -> list[str]:
    if mode == "all" or since_days <= 0:
        return []
    since_ts = (datetime.now(UTC) - timedelta(days=since_days)).isoformat(timespec="seconds")
    return ["--since", since_ts]


def _run(cmd: list[str], env: dict[str, str]) -> int:
    result = subprocess.run(cmd, env=env)
    return result.returncode


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
    header = (
        f"mode={cfg.mode} since_days={cfg.since_days} "
        f"limit={cfg.discovery_limit} log_level={cfg.log_level}"
    )
    console.print(Panel(header, title="OpenAmnesia E2E", border_style="cyan"))

    sources = _resolve_sources(config_path)
    if not sources:
        console.print("[bold red]No enabled sources in config.[/bold red]")
        return 2

    env = dict(os.environ)
    env["AMNESIA_LOG_LEVEL"] = cfg.log_level

    stages = ["ingest"] + [f"discover:{src}" for src in sources]
    since_args = _since_arg(cfg.mode, cfg.since_days)

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("start", total=len(stages))
        progress.update(task, description="ingest")
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

    console.print("[bold green]E2E complete.[/bold green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
