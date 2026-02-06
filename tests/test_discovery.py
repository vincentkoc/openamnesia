from __future__ import annotations

from datetime import UTC, datetime

from amnesia.models import Event
from amnesia.pipeline.cluster_enrich import enrich_clusters
from amnesia.pipeline.clustering import cluster_embeddings
from amnesia.pipeline.embedding import HashEmbeddingProvider, embed_events


def test_embed_cluster_enrich_pipeline() -> None:
    events = [
        Event(
            event_id="e1",
            ts=datetime(2026, 2, 6, 1, 0, tzinfo=UTC),
            source="imessage",
            session_id="s1",
            turn_index=0,
            actor="me",
            content="Meeting in London about project openamnesia roadmap",
        ),
        Event(
            event_id="e2",
            ts=datetime(2026, 2, 6, 1, 1, tzinfo=UTC),
            source="imessage",
            session_id="s1",
            turn_index=1,
            actor="contact",
            content="London project timeline and scope discussion",
        ),
    ]
    embeddings = embed_events(events, provider=HashEmbeddingProvider(dimensions=64)).embeddings
    assert len(embeddings) == 2

    clustered = cluster_embeddings({event.event_id: event for event in events}, embeddings)
    assert len(clustered.clusters) >= 1
    assert len(clustered.memberships) == 2

    enrichments = enrich_clusters(
        clustered.clusters, clustered.memberships, {event.event_id: event for event in events}
    )
    assert len(enrichments) >= 1
    assert enrichments[0].summary
