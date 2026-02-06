"""Programmatic iMessage SQLite ingestion SDK."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from amnesia.config import StoreConfig
from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.imessage import IMessageConnector
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
from amnesia.models import IngestAudit, SourceStatus, utc_now
from amnesia.pipeline.entities import extract_entities
from amnesia.pipeline.extract import annotate_moments
from amnesia.pipeline.momentize import momentize_sessions
from amnesia.pipeline.normalize import normalize_records
from amnesia.pipeline.sessionize import sessionize_events
from amnesia.store.factory import build_store
from amnesia.utils.macos import open_full_disk_access_settings


@dataclass(slots=True)
class IMessageIngestConfig:
    db_path: str = "~/Library/Messages/chat.db"
    store_dsn: str = "sqlite:///./data/amnesia.db"
    state_path: str = ".amnesia_imessage_sqlite_state.yaml"
    limit: int = 5000
    entity_granularity: str = "week"
    reset_state: bool = False
    save_state: bool = True
    since: str | None = None
    until: str | None = None
    include_groups: list[str] = field(default_factory=list)
    exclude_groups: list[str] = field(default_factory=list)
    include_actors: list[str] = field(default_factory=list)
    exclude_actors: list[str] = field(default_factory=list)
    include_contains: list[str] = field(default_factory=list)
    exclude_contains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IMessageIngestResult:
    source: str
    seen: int
    ingested: int
    filtered: int
    groups_seen: int
    events: int
    sessions: int
    moments: int
    inserted_events: int
    inserted_sessions: int
    inserted_moments: int
    inserted_mentions: int
    inserted_rollups: int
    top_people: list[tuple[str, int]]
    top_places: list[tuple[str, int]]
    top_projects: list[tuple[str, int]]
    state_path: str
    store_dsn: str
    error: str | None = None
    hint: str | None = None
    disk_access_request_attempted: bool = False
    disk_access_settings_opened: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "seen": self.seen,
            "ingested": self.ingested,
            "filtered": self.filtered,
            "groups_seen": self.groups_seen,
            "events": self.events,
            "sessions": self.sessions,
            "moments": self.moments,
            "inserted_events": self.inserted_events,
            "inserted_sessions": self.inserted_sessions,
            "inserted_moments": self.inserted_moments,
            "inserted_mentions": self.inserted_mentions,
            "inserted_rollups": self.inserted_rollups,
            "top_people": self.top_people,
            "top_places": self.top_places,
            "top_projects": self.top_projects,
            "state_path": self.state_path,
            "store_dsn": self.store_dsn,
            "error": self.error,
            "hint": self.hint,
            "disk_access_request_attempted": self.disk_access_request_attempted,
            "disk_access_settings_opened": self.disk_access_settings_opened,
        }


def run_imessage_ingest(config: IMessageIngestConfig) -> IMessageIngestResult:
    state_path = Path(config.state_path)
    state_doc = _load_state(state_path)
    source_state = {} if config.reset_state else state_doc.get("source_state", {})

    connector = IMessageConnector(
        settings=ConnectorSettings(
            source_name="imessage",
            root_path=Path("./ingest/imessage"),
            pattern="*.jsonl",
            options={
                "mode": "sqlite",
                "db_path": config.db_path,
                "limit": config.limit,
            },
        )
    )
    try:
        poll = connector.poll(source_state)
    except Exception as exc:
        request_attempted = False
        request_opened = False
        if AUTO_REQUEST_DISK_ACCESS_ON_PERMISSION_ERROR:
            request_attempted = True
            request_opened = open_full_disk_access_settings()
        return IMessageIngestResult(
            source="imessage",
            seen=0,
            ingested=0,
            filtered=0,
            groups_seen=0,
            events=0,
            sessions=0,
            moments=0,
            inserted_events=0,
            inserted_sessions=0,
            inserted_moments=0,
            inserted_mentions=0,
            inserted_rollups=0,
            top_people=[],
            top_places=[],
            top_projects=[],
            state_path=str(state_path),
            store_dsn=config.store_dsn,
            error=str(exc),
            hint=(
                "Grant Full Disk Access to your terminal/python app, or use imessage jsonl exports."
            ),
            disk_access_request_attempted=request_attempted,
            disk_access_settings_opened=request_opened,
        )

    filter_pipeline = _build_filters(config)
    records, dropped = filter_pipeline.apply(poll.records)

    events = normalize_records(records)
    sessions = sessionize_events(events)
    moments = annotate_moments(momentize_sessions(sessions), events)
    entities = extract_entities(events, granularity=config.entity_granularity)

    store = build_store(StoreConfig(backend="sqlite", dsn=config.store_dsn))
    store.init_schema()
    inserted_events = store.save_events(events)
    inserted_sessions = store.save_sessions(sessions)
    inserted_moments = store.save_moments(moments)
    inserted_mentions = store.save_entity_mentions(entities.mentions)
    inserted_rollups = store.save_entity_rollups(entities.rollups)

    store.save_source_status(
        SourceStatus(
            source="imessage",
            status="ingesting" if records else "idle",
            last_poll_ts=utc_now(),
            records_seen=poll.stats.items_seen,
            records_ingested=len(records),
            error_message=None,
        )
    )
    store.append_ingest_audit(
        IngestAudit(
            audit_id=str(uuid.uuid4()),
            ts=utc_now(),
            source="imessage",
            event_count=len(events),
            session_count=len(sessions),
            moment_count=len(moments),
            skill_count=0,
            details_json={
                "records_filtered": dropped,
                "groups_seen": poll.stats.groups_seen,
                "item_counts_by_group": poll.stats.item_counts_by_group,
                "inserted_mentions": inserted_mentions,
                "inserted_rollups": inserted_rollups,
            },
        )
    )
    store.close()

    if config.save_state:
        state_doc["source_state"] = poll.state
        _save_state(state_path, state_doc)

    return IMessageIngestResult(
        source="imessage",
        seen=poll.stats.items_seen,
        ingested=len(records),
        filtered=dropped,
        groups_seen=poll.stats.groups_seen,
        events=len(events),
        sessions=len(sessions),
        moments=len(moments),
        inserted_events=inserted_events,
        inserted_sessions=inserted_sessions,
        inserted_moments=inserted_moments,
        inserted_mentions=inserted_mentions,
        inserted_rollups=inserted_rollups,
        top_people=_top_mentions(entities.mentions, "person"),
        top_places=_top_mentions(entities.mentions, "place"),
        top_projects=_top_mentions(entities.mentions, "project"),
        state_path=str(state_path),
        store_dsn=config.store_dsn,
    )


def dump_imessage_config(path: Path, config: IMessageIngestConfig) -> None:
    payload = {
        "db_path": config.db_path,
        "store_dsn": config.store_dsn,
        "state_path": config.state_path,
        "limit": config.limit,
        "entity_granularity": config.entity_granularity,
        "since": config.since,
        "until": config.until,
        "include_groups": config.include_groups,
        "exclude_groups": config.exclude_groups,
        "include_actors": config.include_actors,
        "exclude_actors": config.exclude_actors,
        "include_contains": config.include_contains,
        "exclude_contains": config.exclude_contains,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False)


def load_imessage_config(path: Path) -> IMessageIngestConfig:
    if not path.exists():
        return IMessageIngestConfig()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return IMessageIngestConfig(
        db_path=str(raw.get("db_path", "~/Library/Messages/chat.db")),
        store_dsn=str(raw.get("store_dsn", "sqlite:///./data/amnesia.db")),
        state_path=str(raw.get("state_path", ".amnesia_imessage_sqlite_state.yaml")),
        limit=int(raw.get("limit", 5000)),
        entity_granularity=str(raw.get("entity_granularity", "week")),
        since=raw.get("since"),
        until=raw.get("until"),
        include_groups=list(raw.get("include_groups", [])),
        exclude_groups=list(raw.get("exclude_groups", [])),
        include_actors=list(raw.get("include_actors", [])),
        exclude_actors=list(raw.get("exclude_actors", [])),
        include_contains=list(raw.get("include_contains", [])),
        exclude_contains=list(raw.get("exclude_contains", [])),
    )


def result_to_json(result: IMessageIngestResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True, indent=2)


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(state, fh, sort_keys=True)


def _build_filters(config: IMessageIngestConfig) -> SourceFilterPipeline:
    pipeline = SourceFilterPipeline()
    if config.include_contains:
        pipeline.add(make_include_contains_filter(config.include_contains))
    if config.exclude_contains:
        pipeline.add(make_exclude_contains_filter(config.exclude_contains))
    if config.include_groups:
        pipeline.add(make_include_groups_filter(config.include_groups))
    if config.exclude_groups:
        pipeline.add(make_exclude_groups_filter(config.exclude_groups))
    if config.include_actors:
        pipeline.add(make_include_actors_filter(config.include_actors))
    if config.exclude_actors:
        pipeline.add(make_exclude_actors_filter(config.exclude_actors))
    pipeline.add(make_since_filter(parse_iso_ts(config.since)))
    pipeline.add(make_until_filter(parse_iso_ts(config.until)))
    return pipeline


def _top_mentions(mentions, entity_type: str) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter(
        mention.entity_value for mention in mentions if mention.entity_type == entity_type
    )
    return counter.most_common(10)
