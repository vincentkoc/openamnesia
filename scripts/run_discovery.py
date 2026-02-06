#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("XDG_CACHE_HOME", str(Path(".cache").resolve()))
os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))

from amnesia.config import StoreConfig
from amnesia.pipeline.cluster_enrich import ClusterEnrichmentOptions, enrich_clusters
from amnesia.pipeline.clustering import cluster_embeddings
from amnesia.pipeline.embedding import HashEmbeddingProvider, embed_events
from amnesia.store.factory import build_store
from amnesia.utils.logging import setup_logging


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Semantic discovery: embed -> cluster -> enrich")
    parser.add_argument("--source", required=True)
    parser.add_argument("--store-dsn", default="sqlite:///./data/amnesia.db")
    parser.add_argument("--since")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--dims", type=int, default=128)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--model", default="gpt-5-nano")
    parser.add_argument("--llm-max-clusters", type=int, default=12)
    parser.add_argument("--llm-max-tokens", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    setup_logging()
    store = build_store(StoreConfig(backend="sqlite", dsn=args.store_dsn))
    store.init_schema()

    events = store.list_events_for_source(source=args.source, since_ts=args.since, limit=args.limit)
    events_by_id = {event.event_id: event for event in events}
    embedding_result = embed_events(
        events,
        provider=HashEmbeddingProvider(dimensions=max(16, args.dims)),
    )
    cluster_result = cluster_embeddings(events_by_id, embedding_result.embeddings)
    enrichments = enrich_clusters(
        cluster_result.clusters,
        cluster_result.memberships,
        events_by_id,
        options=ClusterEnrichmentOptions(
            use_llm=args.use_llm,
            model=args.model,
            max_clusters=max(1, args.llm_max_clusters),
            max_tokens=max(32, args.llm_max_tokens),
        ),
    )

    inserted_embeddings = store.save_event_embeddings(embedding_result.embeddings)
    inserted_clusters = store.save_event_clusters(cluster_result.clusters)
    inserted_memberships = store.save_cluster_memberships(cluster_result.memberships)
    inserted_enrichments = store.save_cluster_enrichments(enrichments)
    store.close()

    payload = {
        "source": args.source,
        "events": len(events),
        "embeddings": len(embedding_result.embeddings),
        "clusters": len(cluster_result.clusters),
        "memberships": len(cluster_result.memberships),
        "enrichments": len(enrichments),
        "inserted": {
            "embeddings": inserted_embeddings,
            "clusters": inserted_clusters,
            "memberships": inserted_memberships,
            "enrichments": inserted_enrichments,
        },
        "top_clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "label": cluster.label,
                "size": cluster.size,
            }
            for cluster in cluster_result.clusters[:10]
        ],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    print("Discovery complete")
    print(
        f"source={payload['source']} events={payload['events']} embeddings={payload['embeddings']} "
        f"clusters={payload['clusters']} memberships={payload['memberships']} "
        f"enrichments={payload['enrichments']}"
    )
    print(
        "inserted "
        f"embeddings={inserted_embeddings} clusters={inserted_clusters} "
        f"memberships={inserted_memberships} enrichments={inserted_enrichments}"
    )
    for item in payload["top_clusters"][:5]:
        print(f"- {item['size']} :: {item['label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
