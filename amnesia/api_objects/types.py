"""Type-safe objects for ingestion service APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SourceState:
    """Connector state persisted per source between ingestion polls."""

    values: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)


@dataclass(slots=True)
class SourceStats:
    """Per-poll source counters used by connectors and run summaries."""

    items_seen: int = 0
    groups_seen: int = 0
    item_counts_by_group: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourcePollStartedEvent:
    source: str
    state_keys: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourcePollCompletedEvent:
    source: str
    items_seen: int
    items_ingested: int
    items_filtered: int
    groups_seen: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourcePollErrorEvent:
    source: str
    error: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceIngestionSummary:
    source: str
    status: str
    records_seen: int
    records_ingested: int
    records_filtered: int = 0
    groups_seen: int = 0
    group_item_counts: dict[str, int] = field(default_factory=dict)
    inserted_events: int = 0
    inserted_sessions: int = 0
    inserted_moments: int = 0
    inserted_skills: int = 0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class IngestionRunSummary:
    started_at: datetime
    ended_at: datetime
    once: bool
    source_summaries: list[SourceIngestionSummary] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.ended_at - self.started_at).total_seconds())

    @property
    def total_records_seen(self) -> int:
        return sum(item.records_seen for item in self.source_summaries)

    @property
    def total_records_ingested(self) -> int:
        return sum(item.records_ingested for item in self.source_summaries)

    @property
    def total_records_filtered(self) -> int:
        return sum(item.records_filtered for item in self.source_summaries)

    @property
    def total_groups_seen(self) -> int:
        return sum(item.groups_seen for item in self.source_summaries)

    @property
    def total_events(self) -> int:
        return sum(item.inserted_events for item in self.source_summaries)

    @property
    def total_sessions(self) -> int:
        return sum(item.inserted_sessions for item in self.source_summaries)

    @property
    def total_moments(self) -> int:
        return sum(item.inserted_moments for item in self.source_summaries)

    @property
    def total_skills(self) -> int:
        return sum(item.inserted_skills for item in self.source_summaries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "once": self.once,
            "duration_seconds": self.duration_seconds,
            "totals": {
                "records_seen": self.total_records_seen,
                "records_ingested": self.total_records_ingested,
                "records_filtered": self.total_records_filtered,
                "groups_seen": self.total_groups_seen,
                "events": self.total_events,
                "sessions": self.total_sessions,
                "moments": self.total_moments,
                "skills": self.total_skills,
            },
            "sources": [item.to_dict() for item in self.source_summaries],
        }
