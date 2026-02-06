from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Event:
    event_id: str
    ts: datetime
    source: str
    session_id: str
    turn_index: int
    actor: str
    content: str
    tool_name: str | None = None
    tool_status: str | None = None
    tool_args_json: dict[str, Any] | None = None
    tool_result_json: dict[str, Any] | None = None
    meta_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Session:
    session_key: str
    session_id: str
    source: str
    start_ts: datetime
    end_ts: datetime
    summary: str
    meta_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Moment:
    moment_id: str
    session_key: str
    start_turn: int
    end_turn: int
    intent: str
    outcome: str
    friction_score: float
    summary: str
    evidence_json: dict[str, Any] = field(default_factory=dict)
    artifacts_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceStatus:
    source: str
    status: str
    last_poll_ts: datetime
    records_seen: int
    records_ingested: int
    error_message: str | None = None


@dataclass(slots=True)
class IngestAudit:
    audit_id: str
    ts: datetime
    source: str
    event_count: int
    session_count: int
    moment_count: int
    skill_count: int
    details_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EntityMention:
    mention_id: str
    event_id: str
    ts: datetime
    source: str
    entity_type: str
    entity_value: str
    confidence: float
    meta_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EntityRollup:
    rollup_id: str
    bucket_start_ts: datetime
    bucket_granularity: str
    source: str
    entity_type: str
    entity_value: str
    mention_count: int
    meta_json: dict[str, Any] = field(default_factory=dict)
