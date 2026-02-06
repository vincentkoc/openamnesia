"""Cluster-level enrichment, optionally using LLMs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC

from amnesia.inference.litellm_provider import LiteLLMProvider
from amnesia.models import ClusterEnrichment, ClusterMembership, Event, EventCluster, utc_now


@dataclass(slots=True)
class ClusterEnrichmentOptions:
    use_llm: bool = False
    model: str = "gpt-5-nano"
    max_clusters: int = 12
    max_tokens: int = 80
    timeout_seconds: int = 30
    on_progress: Callable[[dict[str, object]], None] | None = None


def enrich_clusters(
    clusters: list[EventCluster],
    memberships: list[ClusterMembership],
    events_by_id: dict[str, Event],
    *,
    options: ClusterEnrichmentOptions | None = None,
) -> list[ClusterEnrichment]:
    cfg = options or ClusterEnrichmentOptions()
    selected = clusters[: max(0, cfg.max_clusters)]
    by_cluster: dict[str, list[ClusterMembership]] = {}
    for item in memberships:
        by_cluster.setdefault(item.cluster_id, []).append(item)

    provider = LiteLLMProvider(model=cfg.model) if cfg.use_llm else None
    enrichments: list[ClusterEnrichment] = []
    for cluster in selected:
        members = sorted(by_cluster.get(cluster.cluster_id, []), key=lambda it: it.distance)
        exemplar_texts: list[str] = []
        for member in members[:5]:
            event = events_by_id.get(member.event_id)
            if event is None:
                continue
            exemplar_texts.append(" ".join(event.content.split())[:240])

        payload = {
            "cluster_id": cluster.cluster_id,
            "label": cluster.label,
            "size": cluster.size,
            "source": cluster.source,
            "examples": exemplar_texts,
        }

        provider_name = "heuristic"
        summary = _heuristic_summary(payload)
        llm_attempted = False
        llm_succeeded = False
        llm_error: str | None = None
        if provider is not None and exemplar_texts:
            llm_attempted = True
            provider_name = f"litellm:{cfg.model}"
            summary, llm_succeeded, llm_error = _llm_summary(
                provider,
                payload,
                fallback=summary,
                max_tokens=cfg.max_tokens,
                timeout_seconds=cfg.timeout_seconds,
            )

        enrichment_id = hashlib.sha256(
            f"{cluster.cluster_id}|{provider_name}|{summary}".encode()
        ).hexdigest()
        enrichments.append(
            ClusterEnrichment(
                enrichment_id=enrichment_id,
                cluster_id=cluster.cluster_id,
                ts=utc_now().astimezone(UTC),
                source=cluster.source,
                provider=provider_name,
                summary=summary[:800],
                payload_json={
                    **payload,
                    "llm_attempted": llm_attempted,
                    "llm_succeeded": llm_succeeded,
                    "llm_error": llm_error,
                },
            )
        )
        if cfg.on_progress is not None:
            cfg.on_progress(
                {
                    "cluster_id": cluster.cluster_id,
                    "size": cluster.size,
                    "provider": provider_name,
                    "llm_attempted": llm_attempted,
                    "llm_succeeded": llm_succeeded,
                    "llm_error": llm_error,
                }
            )
    return enrichments


def _heuristic_summary(payload: dict[str, object]) -> str:
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        examples = []
    lead = examples[0] if examples else ""
    return (
        f"Cluster {payload.get('cluster_id')} ({payload.get('size')} events) "
        f"appears to focus on: {lead}"
    )


def _llm_summary(
    provider: LiteLLMProvider,
    payload: dict[str, object],
    *,
    fallback: str,
    max_tokens: int,
    timeout_seconds: int,
) -> tuple[str, bool, str | None]:
    system = (
        "You summarize telemetry clusters. Return one concise sentence describing "
        "shared intent/outcome/friction."
    )
    user = json.dumps(payload, ensure_ascii=True)
    try:
        response = provider.complete(
            system=system,
            user=user,
            max_tokens=max_tokens,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return fallback, False, str(exc)
    if response:
        return response, True, None
    return fallback, False, "empty_response"
