#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from amnesia.config import SourceConfig, load_config
from amnesia.connectors.registry import build_connectors
from amnesia.filters import (
    SourceFilterPipeline,
    make_exclude_contains_filter,
    make_include_contains_filter,
)
from amnesia.internal.events import EventBus


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
    cfg = load_config(args.config)

    source_cfg = next((src for src in cfg.sources if src.name == args.source and src.enabled), None)
    if source_cfg is None:
        raise SystemExit(f"Source '{args.source}' is not configured and enabled in {args.config}")

    connectors = build_connectors([source_cfg])
    connector = connectors[0]
    if args.source == "imessage" and "mode" not in source_cfg.options:
        source_cfg.options["mode"] = "sqlite"

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
    poll_result = connector.poll(source_state)
    pipeline = _build_filter_pipeline(source_cfg)
    filtered_records, dropped = pipeline.apply(poll_result.records)
    bus.emit(
        "source.test.completed",
        source=args.source,
        seen=poll_result.stats.items_seen,
        ingested=len(filtered_records),
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
        "items_ingested": len(filtered_records),
        "items_filtered": dropped,
        "groups_seen": poll_result.stats.groups_seen,
        "item_counts_by_group": poll_result.stats.item_counts_by_group,
        "sample_records": [
            {
                "session_hint": rec.session_hint,
                "group_hint": rec.group_hint,
                "actor": rec.actor,
                "content": rec.content,
            }
            for rec in filtered_records[: max(0, args.sample)]
        ],
        "events": recent_events,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    console = Console()
    console.print(
        f"[bold cyan]Source test:[/bold cyan] {args.source} "
        f"seen={payload['items_seen']} ingested={payload['items_ingested']} "
        f"filtered={payload['items_filtered']} groups={payload['groups_seen']}"
    )

    groups_table = Table(title="Groups", show_header=True, header_style="bold cyan")
    groups_table.add_column("Group")
    groups_table.add_column("Items", justify="right")
    for group, count in sorted(payload["item_counts_by_group"].items()):
        groups_table.add_row(group, str(count))
    console.print(groups_table)

    records_table = Table(title="Sample Records", show_header=True, header_style="bold cyan")
    records_table.add_column("Actor")
    records_table.add_column("Group")
    records_table.add_column("Content", overflow="fold")
    for item in payload["sample_records"]:
        records_table.add_row(item["actor"], str(item.get("group_hint") or "-"), item["content"])
    console.print(records_table)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
