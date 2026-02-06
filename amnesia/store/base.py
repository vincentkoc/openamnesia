from __future__ import annotations

from typing import Protocol

from amnesia.models import (
    EntityMention,
    EntityRollup,
    Event,
    IngestAudit,
    Moment,
    Session,
    SourceStatus,
)


class Store(Protocol):
    def init_schema(self) -> None: ...

    def save_events(self, events: list[Event]) -> int: ...

    def save_sessions(self, sessions: list[Session]) -> int: ...

    def save_moments(self, moments: list[Moment]) -> int: ...

    def save_skill_candidates(self, skills: list[dict]) -> int: ...

    def save_source_status(self, status: SourceStatus) -> None: ...

    def list_source_status(self) -> list[SourceStatus]: ...

    def append_ingest_audit(self, audit: IngestAudit) -> None: ...

    def save_entity_mentions(self, mentions: list[EntityMention]) -> int: ...

    def save_entity_rollups(self, rollups: list[EntityRollup]) -> int: ...

    def close(self) -> None: ...
