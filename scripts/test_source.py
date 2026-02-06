#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from amnesia import __version__
from amnesia.config import SourceConfig, load_config
from amnesia.connectors.registry import build_connectors
from amnesia.constants import AUTO_REQUEST_DISK_ACCESS_ON_PERMISSION_ERROR
from amnesia.filters import (
    SourceFilterPipeline,
    make_exclude_actors_filter,
    make_exclude_contains_filter,
    make_exclude_groups_filter,
    make_include_actors_filter,
    make_include_contains_filter,
    make_include_groups_filter,
    make_since_filter,
    make_until_filter,
    parse_iso_ts,
)
from amnesia.internal.events import EventBus
from amnesia.utils.display.terminal import print_banner
from amnesia.utils.macos import open_full_disk_access_settings


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(state, fh, sort_keys=True)


def _build_filter_pipeline(source_cfg: SourceConfig) -> SourceFilterPipeline:
    pipeline = SourceFilterPipeline()
    if source_cfg.include_contains:
        pipeline.add(make_include_contains_filter(source_cfg.include_contains))
    if source_cfg.exclude_contains:
        pipeline.add(make_exclude_contains_filter(source_cfg.exclude_contains))
    if source_cfg.include_groups:
        pipeline.add(make_include_groups_filter(source_cfg.include_groups))
    if source_cfg.exclude_groups:
        pipeline.add(make_exclude_groups_filter(source_cfg.exclude_groups))
    if source_cfg.include_actors:
        pipeline.add(make_include_actors_filter(source_cfg.include_actors))
    if source_cfg.exclude_actors:
        pipeline.add(make_exclude_actors_filter(source_cfg.exclude_actors))
    pipeline.add(make_since_filter(parse_iso_ts(source_cfg.since_ts)))
    pipeline.add(make_until_filter(parse_iso_ts(source_cfg.until_ts)))
    return pipeline


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test a single source connector ingestion pass")
    parser.add_argument("--config", default="config.yaml", help="Config path")
    parser.add_argument("--source", required=True, help="Source name (e.g. imessage)")
    parser.add_argument(
        "--state-path",
        default="./.amnesia_source_test_state.yaml",
        help="Persistent source state file",
    )
    parser.add_argument("--sample", type=int, default=5, help="Show first N records")
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="Sample ordering by timestamp (desc=newest first)",
    )
    parser.add_argument("--group-limit", type=int, default=20, help="Max groups to display")
    parser.add_argument(
        "--include-group",
        action="append",
        default=[],
        help="Group/chat include filter (contains, repeatable)",
    )
    parser.add_argument(
        "--exclude-group",
        action="append",
        default=[],
        help="Group/chat exclude filter (contains, repeatable)",
    )
    parser.add_argument(
        "--include-actor",
        action="append",
        default=[],
        help="Actor include filter (contains, repeatable)",
    )
    parser.add_argument(
        "--exclude-actor",
        action="append",
        default=[],
        help="Actor exclude filter (contains, repeatable)",
    )
    parser.add_argument("--since", help="Only include records >= ISO timestamp")
    parser.add_argument("--until", help="Only include records <= ISO timestamp")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--no-save-state",
        action="store_true",
        help="Do not persist source offsets after poll",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Ignore persisted state for this source before polling",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    console = Console()
    if not args.json:
        print_banner()
    cfg = load_config(args.config)

    source_cfg = next((src for src in cfg.sources if src.name == args.source and src.enabled), None)
    if source_cfg is None:
        message = f"Source '{args.source}' is not configured and enabled in {args.config}"
        if args.json:
            print(
                json.dumps({"source": args.source, "error": message}, ensure_ascii=True, indent=2)
            )
            return 2
        console.print(Panel(message, title="Source Error", border_style="red"))
        return 2

    connectors = build_connectors([source_cfg])
    connector = connectors[0]
    if args.source == "imessage" and "mode" not in source_cfg.options:
        source_cfg.options["mode"] = "sqlite"

    # CLI filters extend config filters for quick experimentation.
    source_cfg.include_groups = [*source_cfg.include_groups, *args.include_group]
    source_cfg.exclude_groups = [*source_cfg.exclude_groups, *args.exclude_group]
    source_cfg.include_actors = [*source_cfg.include_actors, *args.include_actor]
    source_cfg.exclude_actors = [*source_cfg.exclude_actors, *args.exclude_actor]
    if args.since:
        source_cfg.since_ts = args.since
    if args.until:
        source_cfg.until_ts = args.until

    if not args.json:
        mode = str(source_cfg.options.get("mode", "default"))
        console.print(
            Panel(
                "\n".join(
                    [
                        f"version={__version__}",
                        f"source={args.source}",
                        f"config={args.config}",
                        f"mode={mode}",
                        f"reset_state={args.reset_state}",
                        f"sample={args.sample}",
                        f"since={source_cfg.since_ts or '-'}",
                        f"until={source_cfg.until_ts or '-'}",
                        f"include_groups={source_cfg.include_groups}",
                        f"exclude_groups={source_cfg.exclude_groups}",
                        f"include_actors={source_cfg.include_actors}",
                        f"exclude_actors={source_cfg.exclude_actors}",
                    ]
                ),
                title="Source Test Task",
                border_style="cyan",
            )
        )

    state_path = Path(args.state_path)
    state_doc = _load_state(state_path)
    source_state = {}
    if not args.reset_state:
        source_state = state_doc.get("per_source", {}).get(args.source, {})

    bus = EventBus()
    recent_events: list[dict[str, Any]] = []
    bus.subscribe(
        "*",
        lambda evt: recent_events.append({"topic": evt.topic, "payload": evt.payload}),
    )

    bus.emit("source.test.started", source=args.source)
    try:
        poll_result = connector.poll(source_state)
    except Exception as exc:
        bus.emit("source.test.error", source=args.source, error=str(exc))
        request_attempted = False
        request_success = False
        if (
            args.source == "imessage"
            and AUTO_REQUEST_DISK_ACCESS_ON_PERMISSION_ERROR
        ):
            request_attempted = True
            request_success = open_full_disk_access_settings()

        payload = {
            "source": args.source,
            "error": str(exc),
            "hint": (
                "For iMessage on macOS, grant Full Disk Access to your terminal/python app "
                "or set imessage options.mode=jsonl and ingest exports."
            ),
            "disk_access_request_attempted": request_attempted,
            "disk_access_settings_opened": request_success,
            "events": recent_events,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=True, indent=2))
            return 2

        console.print(
            Panel(
                "[bold]Ingestion failed[/bold]\n"
                f"{payload['error']}\n\n"
                f"[dim]{payload['hint']}[/dim]\n"
                f"[dim]Requested settings open: {request_attempted} "
                f"(opened={request_success})[/dim]",
                title=f"Source Error: {args.source}",
                border_style="red",
            )
        )
        return 2
    pipeline = _build_filter_pipeline(source_cfg)
    filtered_records, dropped = pipeline.apply(poll_result.records)
    ordered_records = _order_records(filtered_records, order=args.order)
    bus.emit(
        "source.test.completed",
        source=args.source,
        seen=poll_result.stats.items_seen,
        ingested=len(ordered_records),
        filtered=dropped,
        groups=poll_result.stats.groups_seen,
    )

    if not args.no_save_state:
        state_doc.setdefault("per_source", {})
        state_doc["per_source"][args.source] = poll_result.state
        _save_state(state_path, state_doc)

    payload = {
        "source": args.source,
        "items_seen": poll_result.stats.items_seen,
        "items_ingested": len(ordered_records),
        "items_filtered": dropped,
        "groups_seen": poll_result.stats.groups_seen,
        "item_counts_by_group": poll_result.stats.item_counts_by_group,
        "time_range": _time_range(ordered_records),
        "sample_records": [
            {
                "ts": rec.ts.isoformat() if rec.ts is not None else None,
                "session_hint": rec.session_hint,
                "group_hint": rec.group_hint,
                "actor": rec.actor,
                "content": rec.content,
            }
            for rec in ordered_records[: max(0, args.sample)]
        ],
        "events": recent_events,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    console.print(
        f"[bold cyan]Source test:[/bold cyan] {args.source} "
        f"seen={payload['items_seen']} ingested={payload['items_ingested']} "
        f"filtered={payload['items_filtered']} groups={payload['groups_seen']} "
        f"order={args.order}"
    )

    tr = payload["time_range"]
    if tr["oldest"] is not None:
        console.print(
            f"[dim]Time range:[/dim] oldest={tr['oldest']} newest={tr['newest']} "
            f"(records with timestamps={tr['timestamped_records']})"
        )
    else:
        console.print("[dim]Time range:[/dim] no timestamps available")

    group_rows = _build_group_rows(ordered_records)
    groups_table = Table(title="Groups", show_header=True, header_style="bold cyan")
    groups_table.add_column("Group")
    groups_table.add_column("Items", justify="right")
    groups_table.add_column("Share", justify="right")
    groups_table.add_column("Latest", style="dim")
    total = max(1, len(ordered_records))
    for row in group_rows[: max(0, args.group_limit)]:
        groups_table.add_row(
            row["group"],
            str(row["count"]),
            f"{(row['count'] / total):.1%}",
            row["latest_ts"] or "-",
        )
    console.print(groups_table)

    records_table = Table(title="Sample Records", show_header=True, header_style="bold cyan")
    records_table.add_column("Time", style="dim")
    records_table.add_column("Actor")
    records_table.add_column("Group")
    records_table.add_column("Content", overflow="fold")
    for item in payload["sample_records"]:
        records_table.add_row(
            item["ts"] or "-",
            item["actor"],
            str(item.get("group_hint") or "-"),
            item["content"],
        )
    console.print(records_table)

    return 0


def _order_records(records, order: str):
    def _key(rec) -> tuple[datetime, int]:
        ts = rec.ts if rec.ts is not None else datetime(1970, 1, 1, tzinfo=UTC)
        return (ts, rec.line_number)

    return sorted(records, key=_key, reverse=(order == "desc"))


def _time_range(records) -> dict[str, Any]:
    stamped = [rec.ts for rec in records if rec.ts is not None]
    if not stamped:
        return {"oldest": None, "newest": None, "timestamped_records": 0}
    oldest = min(stamped)
    newest = max(stamped)
    return {
        "oldest": oldest.isoformat(),
        "newest": newest.isoformat(),
        "timestamped_records": len(stamped),
    }


def _build_group_rows(records) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for rec in records:
        group = str(rec.group_hint or rec.session_hint or "unknown_group")
        bucket = grouped.setdefault(group, {"count": 0, "latest_ts": None})
        bucket["count"] += 1
        ts = rec.ts.isoformat() if rec.ts is not None else None
        if ts is not None:
            if bucket["latest_ts"] is None or ts > bucket["latest_ts"]:
                bucket["latest_ts"] = ts

    rows = [
        {"group": group, "count": data["count"], "latest_ts": data["latest_ts"]}
        for group, data in grouped.items()
    ]
    return sorted(rows, key=lambda row: (row["count"], row["latest_ts"] or ""), reverse=True)


if __name__ == "__main__":
    raise SystemExit(main())
