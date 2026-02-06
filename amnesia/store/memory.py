from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

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


@dataclass(slots=True)
class InMemoryStore:
    events: dict[str, Event] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)
    moments: dict[str, Moment] = field(default_factory=dict)
    skills: dict[str, dict] = field(default_factory=dict)
    source_status: dict[str, SourceStatus] = field(default_factory=dict)
    audits: list[IngestAudit] = field(default_factory=list)
    entity_mentions: dict[str, EntityMention] = field(default_factory=dict)
    entity_rollups: dict[str, EntityRollup] = field(default_factory=dict)
    event_embeddings: dict[str, EventEmbedding] = field(default_factory=dict)
    event_clusters: dict[str, EventCluster] = field(default_factory=dict)
    cluster_memberships: dict[str, ClusterMembership] = field(default_factory=dict)
    cluster_enrichments: dict[str, ClusterEnrichment] = field(default_factory=dict)

    def init_schema(self) -> None:
        return

    def save_events(self, events: list[Event]) -> int:
        inserted = 0
        for event in events:
            if event.event_id not in self.events:
                self.events[event.event_id] = event
                inserted += 1
        return inserted

    def save_sessions(self, sessions: list[Session]) -> int:
        inserted = 0
        for session in sessions:
            if session.session_key not in self.sessions:
                self.sessions[session.session_key] = session
                inserted += 1
        return inserted

    def save_moments(self, moments: list[Moment]) -> int:
        inserted = 0
        for moment in moments:
            if moment.moment_id not in self.moments:
                self.moments[moment.moment_id] = moment
                inserted += 1
        return inserted

    def save_skill_candidates(self, skills: list[dict]) -> int:
        inserted = 0
        for skill in skills:
            key = f"{skill['name']}:v0"
            if key not in self.skills:
                inserted += 1
            self.skills[key] = skill
        return inserted

    def save_source_status(self, status: SourceStatus) -> None:
        self.source_status[status.source] = status

    def list_source_status(self) -> list[SourceStatus]:
        return sorted(self.source_status.values(), key=lambda item: item.source)

    def append_ingest_audit(self, audit: IngestAudit) -> None:
        self.audits.append(audit)

    def save_entity_mentions(self, mentions: list[EntityMention]) -> int:
        inserted = 0
        for mention in mentions:
            if mention.mention_id not in self.entity_mentions:
                self.entity_mentions[mention.mention_id] = mention
                inserted += 1
        return inserted

    def save_entity_rollups(self, rollups: list[EntityRollup]) -> int:
        inserted = 0
        for rollup in rollups:
            if rollup.rollup_id not in self.entity_rollups:
                self.entity_rollups[rollup.rollup_id] = rollup
                inserted += 1
        return inserted

    def save_event_embeddings(self, embeddings: list[EventEmbedding]) -> int:
        inserted = 0
        for embedding in embeddings:
            if embedding.embedding_id not in self.event_embeddings:
                self.event_embeddings[embedding.embedding_id] = embedding
                inserted += 1
        return inserted

    def save_event_clusters(self, clusters: list[EventCluster]) -> int:
        inserted = 0
        for cluster in clusters:
            if cluster.cluster_id not in self.event_clusters:
                self.event_clusters[cluster.cluster_id] = cluster
                inserted += 1
        return inserted

    def save_cluster_memberships(self, memberships: list[ClusterMembership]) -> int:
        inserted = 0
        for membership in memberships:
            if membership.membership_id not in self.cluster_memberships:
                self.cluster_memberships[membership.membership_id] = membership
                inserted += 1
        return inserted

    def save_cluster_enrichments(self, enrichments: list[ClusterEnrichment]) -> int:
        inserted = 0
        for enrichment in enrichments:
            if enrichment.enrichment_id not in self.cluster_enrichments:
                self.cluster_enrichments[enrichment.enrichment_id] = enrichment
                inserted += 1
        return inserted

    def list_events_for_source(
        self,
        *,
        source: str,
        since_ts: str | None = None,
        limit: int = 5000,
    ) -> list[Event]:
        events = [event for event in self.events.values() if event.source == source]
        if since_ts:
            threshold = datetime.fromisoformat(str(since_ts).replace("Z", "+00:00"))
            if threshold.tzinfo is None:
                threshold = threshold.replace(tzinfo=UTC)
            events = [event for event in events if event.ts >= threshold]
        events.sort(key=lambda item: item.ts, reverse=True)
        return events[: max(0, limit)]

    def close(self) -> None:
        return
