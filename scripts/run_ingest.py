#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, timedelta
from pathlib import Path

import yaml

from amnesia.config import SourceConfig, load_config
from amnesia.ingest.spool import JsonlSpool
from amnesia.ingest.trawl import IncrementalFileTrawler, TrawlState
from amnesia.models import IngestAudit, SourceStatus, utc_now
from amnesia.pipeline.entities import extract_entities
from amnesia.pipeline.extract import annotate_moments
from amnesia.pipeline.momentize import momentize_sessions
from amnesia.pipeline.normalize import normalize_records
from amnesia.pipeline.sessionize import sessionize_events
from amnesia.store.factory import build_store
from amnesia.connectors.registry import build_connectors
from amnesia.utils.logging import get_logger, setup_logging
from amnesia.exports.memory import MemoryExportConfig, export_memory
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

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback for minimal envs
    tqdm = None


@dataclass(slots=True)
class SourceRunResult:
    source: str
    files_scanned: int
    files_changed: int
    bytes_read: int
    records: int
    events: int
    sessions: int
    moments: int
    people_mentions: int
    place_mentions: int
    project_mentions: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scalable ingest pipeline")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--state-path", default=".amnesia_trawl_state.yaml")
    parser.add_argument("--spool-dir", default=".amnesia_spool")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--max-records-per-source", type=int)
    parser.add_argument("--entity-granularity", choices=["day", "week", "month"], default="week")
    parser.add_argument("--include-groups", action="append", default=[])
    parser.add_argument("--exclude-groups", action="append", default=[])
    parser.add_argument("--include-contains", action="append", default=[])
    parser.add_argument("--exclude-contains", action="append", default=[])
    parser.add_argument("--include-actors", action="append", default=[])
    parser.add_argument("--exclude-actors", action="append", default=[])
    parser.add_argument("--since")
    parser.add_argument("--since-days", type=int, default=None)
    parser.add_argument("--until")
    parser.add_argument("--reset-state", action="store_true")
    parser.add_argument("--keep-spool", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _save_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=True)


def _iter_sources(config_sources: list[SourceConfig], only: set[str]) -> Iterable[SourceConfig]:
    for source in config_sources:
        if not source.enabled:
            continue
        if only and source.name not in only:
            continue
        yield source


def _is_file_source(source: SourceConfig) -> bool:
    mode = str(source.options.get("mode", "")).strip().lower()
    return source.name != "imessage" or mode == "jsonl"


def _use_connector(source: SourceConfig) -> bool:
    return bool(source.options.get("use_connector", False))


def _split_terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        if not value:
            continue
        for part in str(value).split(","):
            item = part.strip()
            if item:
                terms.append(item)
    return terms


def _merge_terms(cli_terms: list[str], cfg_terms: list[str]) -> list[str]:
    return _split_terms(cli_terms) if cli_terms else list(cfg_terms)


def _build_filter_pipeline(source_cfg: SourceConfig, args: argparse.Namespace) -> SourceFilterPipeline:
    pipeline = SourceFilterPipeline()
    include_contains = _merge_terms(args.include_contains, source_cfg.include_contains)
    exclude_contains = _merge_terms(args.exclude_contains, source_cfg.exclude_contains)
    include_groups = _merge_terms(args.include_groups, source_cfg.include_groups)
    exclude_groups = _merge_terms(args.exclude_groups, source_cfg.exclude_groups)
    include_actors = _merge_terms(args.include_actors, source_cfg.include_actors)
    exclude_actors = _merge_terms(args.exclude_actors, source_cfg.exclude_actors)

    if include_contains:
        pipeline.add(make_include_contains_filter(include_contains))
    if exclude_contains:
        pipeline.add(make_exclude_contains_filter(exclude_contains))
    if include_groups:
        pipeline.add(make_include_groups_filter(include_groups))
    if exclude_groups:
        pipeline.add(make_exclude_groups_filter(exclude_groups))
    if include_actors:
        pipeline.add(make_include_actors_filter(include_actors))
    if exclude_actors:
        pipeline.add(make_exclude_actors_filter(exclude_actors))

    since_raw = args.since if args.since is not None else source_cfg.since_ts
    if args.since_days is not None and args.since_days > 0:
        since_raw = (utc_now() - timedelta(days=args.since_days)).astimezone(UTC).isoformat()
    until_raw = args.until if args.until is not None else source_cfg.until_ts
    since_ts = parse_iso_ts(since_raw)
    until_ts = parse_iso_ts(until_raw)
    pipeline.add(make_since_filter(since_ts))
    pipeline.add(make_until_filter(until_ts))
    return pipeline


def main() -> int:
    args = _parse_args()
    setup_logging()
    logger = get_logger("amnesia.run_ingest")

    config = load_config(args.config)
    store = build_store(config.store)
    store.init_schema()

    only_sources = set(args.source)
    state_path = Path(args.state_path)
    spool = JsonlSpool(Path(args.spool_dir))
    full_state = _load_state(state_path)
    per_source_state = full_state.get("per_source", {})
    if args.reset_state:
        per_source_state = {}

    results: list[SourceRunResult] = []
    top_entities: dict[str, dict[str, int]] = {
        "person": {},
        "place": {},
        "project": {},
    }

    source_list = list(_iter_sources(config.sources, only_sources))
    source_iter = (
        tqdm(source_list, desc="sources", unit="source")
        if tqdm is not None and not args.json
        else source_list
    )

    for source_cfg in source_iter:
        if not _is_file_source(source_cfg):
            logger.info(
                "Skipping source=%s in run_ingest (use connector path for sqlite-backed sources)",
                source_cfg.name,
            )
            continue

        source_name = source_cfg.name
        pipeline = _build_filter_pipeline(source_cfg, args)
        segments = []
        if _use_connector(source_cfg):
            connector = build_connectors([source_cfg])[0]
            source_state_before = dict(per_source_state.get(source_name, {}))
            poll = connector.poll(source_state_before)
            per_source_state[source_name] = poll.state
            records = poll.records
            trawl_stats = TrawlState.from_dict({}).to_dict()
            files_scanned = len(poll.state)
            files_changed = 1 if poll.stats.items_seen else 0
            bytes_read = 0
            trawl_stats = type(
                "TrawlStatsShim",
                (),
                {
                    "files_scanned": files_scanned,
                    "files_changed": files_changed,
                    "bytes_read": bytes_read,
                    "records_emitted": poll.stats.items_seen,
                },
            )()
        else:
            source_state_before = TrawlState.from_dict(per_source_state.get(source_name, {}))
            source_state_after = TrawlState.from_dict(source_state_before.to_dict())

            trawler = IncrementalFileTrawler(
                source_name=source_name,
                root_path=Path(source_cfg.path).expanduser(),
                pattern=source_cfg.pattern,
            )

            records_iter = trawler.iter_new_records(
                source_state_after,
                limit_records=args.max_records_per_source,
            )
            segments = spool.write_records(records_iter)
            trawl_stats = trawler.collect_stats(source_state_before, source_state_after)
            trawl_stats.records_emitted = sum(segment.record_count for segment in segments)
            per_source_state[source_name] = source_state_after.to_dict()

            records = list(spool.iter_records(segments))
        if records and args.include_groups:
            pre_group_counts = {}
            for record in records:
                key = record.group_hint or record.session_hint or "-"
                pre_group_counts[key] = pre_group_counts.get(key, 0) + 1
        else:
            pre_group_counts = {}

        records, _dropped = pipeline.apply(records)
        if args.include_groups and not records and pre_group_counts:
            top_groups = sorted(pre_group_counts.items(), key=lambda item: item[1], reverse=True)[:5]
            logger.info("No records after include-groups filter for %s. Top groups: %s", source_name, top_groups)
        if args.max_records_per_source is not None:
            records = records[: args.max_records_per_source]
        events = normalize_records(records)
        sessions = sessionize_events(events)
        moments = annotate_moments(momentize_sessions(sessions), events)
        entities = extract_entities(events, granularity=args.entity_granularity)

        store.save_events(events)
        store.save_sessions(sessions)
        store.save_moments(moments)
        store.save_entity_mentions(entities.mentions)
        store.save_entity_rollups(entities.rollups)

        people_mentions = 0
        place_mentions = 0
        project_mentions = 0
        for mention in entities.mentions:
            bucket = top_entities.setdefault(mention.entity_type, {})
            bucket[mention.entity_value] = bucket.get(mention.entity_value, 0) + 1
            if mention.entity_type == "person":
                people_mentions += 1
            elif mention.entity_type == "place":
                place_mentions += 1
            elif mention.entity_type == "project":
                project_mentions += 1

        store.save_source_status(
            SourceStatus(
                source=source_name,
                status="ingesting" if records else "idle",
                last_poll_ts=utc_now(),
                records_seen=trawl_stats.records_emitted,
                records_ingested=len(records),
                error_message=None,
            )
        )

        store.append_ingest_audit(
            IngestAudit(
                audit_id=str(uuid.uuid4()),
                ts=utc_now(),
                source=source_name,
                event_count=len(events),
                session_count=len(sessions),
                moment_count=len(moments),
                skill_count=0,
                details_json={
                    "files_scanned": trawl_stats.files_scanned,
                    "files_changed": trawl_stats.files_changed,
                    "bytes_read": trawl_stats.bytes_read,
                    "segments": [segment.path.name for segment in segments],
                    "connector_mode": _use_connector(source_cfg),
                },
            )
        )

        results.append(
            SourceRunResult(
                source=source_name,
                files_scanned=trawl_stats.files_scanned,
                files_changed=trawl_stats.files_changed,
                bytes_read=trawl_stats.bytes_read,
                records=len(records),
                events=len(events),
                sessions=len(sessions),
                moments=len(moments),
                people_mentions=people_mentions,
                place_mentions=place_mentions,
                project_mentions=project_mentions,
            )
        )

    if config.exports.enabled and config.exports.memory.get("enabled", False):
        mem_cfg = MemoryExportConfig(**config.exports.memory)
        export_memory(dsn=config.store.dsn, cfg=mem_cfg)

        if not args.keep_spool:
            spool.cleanup(segments)

    full_state["per_source"] = per_source_state
    _save_state(state_path, full_state)
    store.close()

    payload = {
        "sources": [asdict(result) for result in results],
        "top_entities": {
            entity_type: sorted(items.items(), key=lambda item: item[1], reverse=True)[:10]
            for entity_type, items in top_entities.items()
        },
        "state_path": str(state_path),
        "spool_dir": str(Path(args.spool_dir)),
        "entity_granularity": args.entity_granularity,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    print("Ingest run complete")
    for item in payload["sources"]:
        print(
            f"- {item['source']}: files={item['files_scanned']} changed={item['files_changed']} "
            f"bytes={item['bytes_read']} records={item['records']} events={item['events']} "
            f"sessions={item['sessions']} moments={item['moments']} "
            f"people={item['people_mentions']} places={item['place_mentions']} "
            f"projects={item['project_mentions']}"
        )
    for entity_type, items in payload["top_entities"].items():
        if not items:
            continue
        print(f"Top {entity_type}:")
        for value, count in items[:5]:
            print(f"  - {value}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
