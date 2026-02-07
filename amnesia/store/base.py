from __future__ import annotations

from typing import Protocol

from amnesia.models import (
    ClusterEnrichment,
    ClusterMembership,
    EntityMention,
    EntityRollup,
    Event,
    EventCluster,
    EventEmbedding,
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

    def list_skills(self, limit: int = 100) -> list[dict]: ...

    def save_source_status(self, status: SourceStatus) -> None: ...

    def list_source_status(self) -> list[SourceStatus]: ...

    def append_ingest_audit(self, audit: IngestAudit) -> None: ...

    def save_entity_mentions(self, mentions: list[EntityMention]) -> int: ...

    def save_entity_rollups(self, rollups: list[EntityRollup]) -> int: ...

    def save_event_embeddings(self, embeddings: list[EventEmbedding]) -> int: ...

    def save_event_clusters(self, clusters: list[EventCluster]) -> int: ...

    def save_cluster_memberships(self, memberships: list[ClusterMembership]) -> int: ...

    def save_cluster_enrichments(self, enrichments: list[ClusterEnrichment]) -> int: ...

    def list_events_for_source(
        self,
        *,
        source: str,
        since_ts: str | None = None,
        limit: int = 5000,
    ) -> list[Event]: ...

    def close(self) -> None: ...
