"""Type-safe objects for ingestion service APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SourceIngestionSummary:
    source: str
    status: str
    records_seen: int
    records_ingested: int
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
                "events": self.total_events,
                "sessions": self.total_sessions,
                "moments": self.total_moments,
                "skills": self.total_skills,
            },
            "sources": [item.to_dict() for item in self.source_summaries],
        }
