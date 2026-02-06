"""Cluster-level enrichment, optionally using LLMs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from typing import Any

from amnesia.inference.litellm_provider import LiteLLMProvider
from amnesia.models import ClusterEnrichment, ClusterMembership, Event, EventCluster, utc_now


@dataclass(slots=True)
class ClusterEnrichmentOptions:
    use_llm: bool = False
    model: str = "gpt-5-nano"
    max_clusters: int = 12
    max_tokens: int = 80
    timeout_seconds: int = 30
    llm_retries: int = 3
    llm_retry_min_seconds: float = 0.5
    llm_retry_max_seconds: float = 4.0
    llm_throttle_seconds: float = 0.0
    fail_fast_on_llm_error: bool = False
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

    provider = (
        LiteLLMProvider(
            model=cfg.model,
            max_retries=cfg.llm_retries,
            retry_min_seconds=cfg.llm_retry_min_seconds,
            retry_max_seconds=cfg.llm_retry_max_seconds,
            throttle_seconds=cfg.llm_throttle_seconds,
        )
        if cfg.use_llm
        else None
    )
    enrichments: list[ClusterEnrichment] = []
    for cluster in selected:
        members = sorted(by_cluster.get(cluster.cluster_id, []), key=lambda it: it.distance)
        exemplar_texts: list[str] = []
        for member in members[:5]:
            event = events_by_id.get(member.event_id)
            if event is None:
                continue
            cleaned = _compact_example_text(event.content)
            if cleaned:
                exemplar_texts.append(cleaned)
            if len(exemplar_texts) >= 3:
                break

        signal_score = _signal_score(cluster.label, exemplar_texts)
        payload = {
            "cluster_id": cluster.cluster_id,
            "label": _compact_example_text(cluster.label)[:64],
            "size": cluster.size,
            "source": cluster.source,
            "examples": exemplar_texts,
            "signal_score": signal_score,
        }

        provider_name = "heuristic"
        summary = _heuristic_summary(payload)
        llm_attempted = False
        llm_succeeded = False
        llm_error: str | None = None
        llm_path = "heuristic"
        extracted: dict[str, Any] = {}
        if provider is not None and exemplar_texts and _is_llm_worthy(payload):
            llm_attempted = True
            provider_name = f"litellm:{cfg.model}"
            summary, llm_succeeded, llm_error, llm_path, extracted = _llm_summary(
                provider,
                payload,
                fallback=summary,
                max_tokens=cfg.max_tokens,
                timeout_seconds=cfg.timeout_seconds,
            )
            if cfg.fail_fast_on_llm_error and not llm_succeeded:
                raise RuntimeError(
                    "Cluster enrichment failed for "
                    f"{cluster.cluster_id}: {llm_error or 'unknown_error'}"
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
                    "llm_path": llm_path,
                    "signal_score": signal_score,
                    "intent": extracted.get("intent"),
                    "outcome": extracted.get("outcome"),
                    "friction": extracted.get("friction"),
                    "confidence": extracted.get("confidence"),
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
                    "llm_path": llm_path,
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
) -> tuple[str, bool, str | None, str, dict[str, Any]]:
    system = (
        "You summarize telemetry clusters. Return strict JSON only with fields: "
        "summary, intent, outcome, friction."
    )
    user = json.dumps(payload, ensure_ascii=True)
    try:
        from pydantic import BaseModel, Field
    except Exception as exc:  # pragma: no cover
        return fallback, False, f"pydantic_unavailable: {exc}"

    class ClusterSummary(BaseModel):
        summary: str = Field(min_length=8, max_length=320)
        intent: str = Field(default="")
        outcome: str = Field(default="")
        friction: str = Field(default="")
        confidence: float = Field(default=0.65, ge=0.0, le=1.0)

    try:
        response: Any = provider.complete_structured(
            system=system,
            user=user,
            response_model=ClusterSummary,
            max_tokens=max_tokens,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        error_text = str(exc)
        if "finish_reason='length'" in error_text or 'finish_reason="length"' in error_text:
            # Last-resort plain-text path when strict JSON exhausts output budget.
            try:
                plain_system = (
                    "Summarize this telemetry cluster in <= 14 words. No JSON, no markdown."
                )
                plain = provider.complete(
                    system=plain_system,
                    user=user,
                    max_tokens=max(96, max_tokens * 2),
                    timeout=timeout_seconds,
                ).strip()
                if plain:
                    return plain, True, None, "plain_fallback", {}
            except Exception as plain_exc:
                error_text = f"{error_text}; plain_fallback={plain_exc}"
        if "Connection error" in error_text or "ConnectError" in error_text:
            error_text = "openai_connection_error: unable to reach provider after retries"
        return fallback, False, error_text, "failed", {}
    summary = str(getattr(response, "summary", "")).strip()
    if summary:
        return (
            summary,
            True,
            None,
            "structured",
            {
                "intent": str(getattr(response, "intent", "")).strip(),
                "outcome": str(getattr(response, "outcome", "")).strip(),
                "friction": str(getattr(response, "friction", "")).strip(),
                "confidence": float(getattr(response, "confidence", 0.65)),
            },
        )
    return fallback, False, "empty_structured_summary", "failed", {}


def _compact_example_text(text: str) -> str:
    compact = " ".join(str(text).split())
    compact = compact.replace("\ufffc", " ")
    compact = re.sub(r"[^\w\s@:/+.#-]", "", compact)
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) < 2:
        return ""
    return compact[:140]


def _is_llm_worthy(payload: dict[str, object]) -> bool:
    return _signal_score(str(payload.get("label", "")), payload.get("examples", [])) >= 0.22


def _signal_score(label: str, examples: object) -> float:
    items = examples if isinstance(examples, list) else []
    corpus = " ".join([str(label), *[str(item) for item in items]]).strip()
    if not corpus:
        return 0.0
    alpha_count = sum(1 for ch in corpus if ch.isalpha())
    digit_count = sum(1 for ch in corpus if ch.isdigit())
    meaningful = alpha_count + digit_count
    return min(1.0, meaningful / max(1.0, len(corpus)))
