from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from amnesia.models import ClusterEnrichment, EventCluster


@dataclass(slots=True)
class MemoryMaterializationResult:
    skill_candidates: list[dict[str, Any]]
    fact_candidates: list[dict[str, Any]]


def materialize_from_enrichments(
    clusters: list[EventCluster],
    enrichments: list[ClusterEnrichment],
) -> MemoryMaterializationResult:
    cluster_by_id = {cluster.cluster_id: cluster for cluster in clusters}
    fact_candidates: list[dict[str, Any]] = []
    skill_seed: list[tuple[str, float, int]] = []

    for enrichment in enrichments:
        payload = enrichment.payload_json or {}
        intent = _clean_token(str(payload.get("intent", "") or ""))
        outcome = _clean_token(str(payload.get("outcome", "") or ""))
        friction = _clean_token(str(payload.get("friction", "") or ""))
        signal_score = float(payload.get("signal_score", 0.0) or 0.0)
        confidence = float(payload.get("confidence", 0.5) or 0.5)
        cluster = cluster_by_id.get(enrichment.cluster_id)
        size = int(cluster.size) if cluster is not None else int(payload.get("size", 0) or 0)

        fact_candidates.append(
            {
                "kind": "cluster_summary",
                "cluster_id": enrichment.cluster_id,
                "summary": enrichment.summary,
                "intent": intent,
                "outcome": outcome,
                "friction": friction,
                "signal_score": round(signal_score, 4),
                "confidence": round(confidence, 4),
                "size": size,
                "provider": enrichment.provider,
            }
        )
        if not intent:
            intent = _infer_intent_from_summary(enrichment.summary)
        if intent:
            skill_seed.append((intent, confidence, max(1, size)))

    skill_candidates = _derive_skill_candidates(skill_seed)
    return MemoryMaterializationResult(
        skill_candidates=skill_candidates,
        fact_candidates=fact_candidates,
    )


def _derive_skill_candidates(skill_seed: list[tuple[str, float, int]]) -> list[dict[str, Any]]:
    count_by_intent: Counter[str] = Counter()
    confidence_sum: dict[str, float] = {}
    support_sum: dict[str, int] = {}
    for intent, confidence, support in skill_seed:
        count_by_intent[intent] += 1
        confidence_sum[intent] = confidence_sum.get(intent, 0.0) + confidence
        support_sum[intent] = support_sum.get(intent, 0) + support

    candidates: list[dict[str, Any]] = []
    for intent, freq in count_by_intent.most_common():
        avg_conf = confidence_sum[intent] / max(1, freq)
        total_support = support_sum[intent]
        candidates.append(
            {
                "name": f"cluster_{intent}",
                "trigger": {"intent": intent},
                "steps": [
                    "collect cluster exemplars",
                    "summarize intent/outcome/friction",
                    "store reusable guidance",
                ],
                "checks": ["summary_present", "intent_present", "cluster_support>=1"],
                "metrics": {
                    "cluster_frequency": freq,
                    "avg_confidence": round(avg_conf, 3),
                    "support_count": total_support,
                },
            }
        )
    return candidates[:10]


def _clean_token(value: str) -> str:
    compact = " ".join(value.split()).strip().lower()
    compact = re.sub(r"[^a-z0-9_ /-]+", "", compact)
    return compact[:80]


def _infer_intent_from_summary(summary: str) -> str:
    low = summary.lower()
    if "barclays" in low or "panel" in low or "open source" in low:
        return "stakeholder_alignment"
    if "intro" in low or "connect" in low or "community" in low:
        return "networking_followup"
    if "ask" in low or "question" in low:
        return "question_preparation"
    if "schedule" in low or "call" in low or "breakfast" in low:
        return "coordination"
    return "cluster_summary_workflow"
