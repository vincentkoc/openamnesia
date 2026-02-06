"""Cluster embedded events to discover repeated semantic patterns."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC

from amnesia.models import ClusterMembership, Event, EventCluster, EventEmbedding, utc_now


@dataclass(slots=True)
class ClusterResult:
    clusters: list[EventCluster]
    memberships: list[ClusterMembership]


def cluster_embeddings(
    events_by_id: dict[str, Event],
    embeddings: list[EventEmbedding],
    *,
    algorithm: str = "prefix-bucket-v1",
) -> ClusterResult:
    # Local deterministic fallback: bucket by most significant embedding dimensions + source.
    # This keeps behavior stable and cheap while we wire pluggable HDBSCAN/ANN later.
    buckets: dict[tuple[str, int, int], list[EventEmbedding]] = defaultdict(list)
    for item in embeddings:
        top = _top_dims(item.vector_json, k=2)
        key = (item.source, top[0], top[1])
        buckets[key].append(item)

    clusters: list[EventCluster] = []
    memberships: list[ClusterMembership] = []

    for bucket_key, items in buckets.items():
        source, dim_a, dim_b = bucket_key
        centroid = _centroid([it.vector_json for it in items])
        sorted_events = sorted(
            (events_by_id.get(it.event_id) for it in items),
            key=lambda event: event.ts if event is not None else utc_now(),
            reverse=True,
        )
        label = _label_for_bucket(sorted_events)
        cluster_id = hashlib.sha256(
            f"{source}|{algorithm}|{dim_a}|{dim_b}|{len(items)}".encode()
        ).hexdigest()
        ts = max((it.ts for it in items), default=utc_now()).astimezone(UTC)

        clusters.append(
            EventCluster(
                cluster_id=cluster_id,
                ts=ts,
                source=source,
                algorithm=algorithm,
                label=label,
                size=len(items),
                centroid_json=centroid,
                meta_json={"bucket_dims": [dim_a, dim_b]},
            )
        )

        for item in items:
            distance = _l2_distance(item.vector_json, centroid)
            membership_id = hashlib.sha256(f"{cluster_id}|{item.event_id}".encode()).hexdigest()
            memberships.append(
                ClusterMembership(
                    membership_id=membership_id,
                    cluster_id=cluster_id,
                    event_id=item.event_id,
                    distance=distance,
                    ts=item.ts.astimezone(UTC),
                    source=source,
                    meta_json={"model": item.model},
                )
            )

    clusters.sort(key=lambda item: (item.size, item.ts), reverse=True)
    return ClusterResult(clusters=clusters, memberships=memberships)


def _top_dims(vector: list[float], *, k: int) -> list[int]:
    indexed = sorted(enumerate(vector), key=lambda item: item[1], reverse=True)
    top = [index for index, _ in indexed[:k]]
    while len(top) < k:
        top.append(0)
    return top


def _centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dims = len(vectors[0])
    out = [0.0] * dims
    for vector in vectors:
        for idx, value in enumerate(vector):
            out[idx] += value
    return [value / len(vectors) for value in out]


def _l2_distance(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _label_for_bucket(events: list[Event | None]) -> str:
    for event in events:
        if event is None:
            continue
        text = " ".join(event.content.split())
        if text:
            return text[:80]
    return "cluster"
