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


@dataclass(slots=True)
class SkillSeed:
    intent: str
    summary: str
    confidence: float
    support: int


_SKILL_PROFILES: dict[str, dict[str, Any]] = {
    "event_planning": {
        "name": "Plan and follow up on events",
        "steps": [
            "capture event details and constraints",
            "list stakeholders and follow-ups",
            "track next actions and deadlines",
        ],
        "checks": ["event_context_present", "next_action_present"],
    },
    "networking_intro": {
        "name": "Create and track introductions",
        "steps": [
            "identify the two parties",
            "collect context and goal",
            "draft intro and follow-up reminders",
        ],
        "checks": ["contacts_present", "intro_goal_present"],
    },
    "contact_capture": {
        "name": "Capture and confirm new contacts",
        "steps": [
            "extract name and source context",
            "confirm spelling and affiliation",
            "store as a contact candidate",
        ],
        "checks": ["person_name_present", "source_context_present"],
    },
    "coordination": {
        "name": "Coordinate schedules and follow-ups",
        "steps": [
            "propose time windows",
            "confirm availability",
            "log next-step reminders",
        ],
        "checks": ["time_reference_present", "followup_intent_present"],
    },
    "stakeholder_alignment": {
        "name": "Align stakeholders on risks and fit",
        "steps": [
            "summarize risk or fit concerns",
            "collect stakeholder positions",
            "record decision blockers",
        ],
        "checks": ["stakeholders_present", "risk_or_fit_present"],
    },
    "research_synthesis": {
        "name": "Synthesize research into next actions",
        "steps": [
            "collect options and constraints",
            "compare trade-offs",
            "recommend next actions",
        ],
        "checks": ["options_present", "decision_context_present"],
    },
    "frontend_terminal_build": {
        "name": "Ship frontend terminal experiences",
        "steps": [
            "define interaction goal",
            "mock terminal flows",
            "implement and validate UX",
        ],
        "checks": ["ux_goal_present", "flow_defined"],
    },
}

_INTENT_ALIASES: dict[str, str] = {
    "networking_followup": "networking_intro",
    "question_preparation": "research_synthesis",
    "stakeholder_alignment": "stakeholder_alignment",
    "coordination": "coordination",
}


def materialize_from_enrichments(
    clusters: list[EventCluster],
    enrichments: list[ClusterEnrichment],
) -> MemoryMaterializationResult:
    cluster_by_id = {cluster.cluster_id: cluster for cluster in clusters}
    fact_candidates: list[dict[str, Any]] = []
    skill_seed: list[SkillSeed] = []

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
        if not intent or intent in {"cluster_summary_workflow"}:
            intent = _infer_intent_from_summary(enrichment.summary)
        if intent:
            skill_seed.append(
                SkillSeed(
                    intent=intent,
                    summary=enrichment.summary or "",
                    confidence=confidence,
                    support=max(1, size),
                )
            )

    skill_candidates = _derive_skill_candidates(skill_seed)
    return MemoryMaterializationResult(
        skill_candidates=skill_candidates,
        fact_candidates=fact_candidates,
    )


def _derive_skill_candidates(skill_seed: list[SkillSeed]) -> list[dict[str, Any]]:
    count_by_key: Counter[str] = Counter()
    confidence_sum: dict[str, float] = {}
    support_sum: dict[str, int] = {}
    intent_samples: dict[str, list[str]] = {}
    summary_samples: dict[str, list[str]] = {}

    for seed in skill_seed:
        skill_key = _classify_skill_key(seed.intent, seed.summary)
        if not skill_key:
            continue
        count_by_key[skill_key] += 1
        confidence_sum[skill_key] = confidence_sum.get(skill_key, 0.0) + seed.confidence
        support_sum[skill_key] = support_sum.get(skill_key, 0) + seed.support
        intent_samples.setdefault(skill_key, []).append(seed.intent)
        summary_samples.setdefault(skill_key, []).append(seed.summary)

    candidates: list[dict[str, Any]] = []
    for skill_key, freq in count_by_key.most_common():
        profile = _SKILL_PROFILES.get(skill_key)
        if not profile:
            continue
        avg_conf = confidence_sum[skill_key] / max(1, freq)
        total_support = support_sum[skill_key]
        sample_intents = sorted(set(intent_samples.get(skill_key, [])))[:3]
        sample_summaries = [
            _clip_summary(summary) for summary in summary_samples.get(skill_key, [])[:2]
        ]
        candidates.append(
            {
                "name": profile["name"],
                "trigger": {"skill_key": skill_key, "sample_intents": sample_intents},
                "steps": profile["steps"],
                "checks": profile["checks"],
                "metrics": {
                    "cluster_frequency": freq,
                    "avg_confidence": round(avg_conf, 3),
                    "support_count": total_support,
                    "sample_summaries": sample_summaries,
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


def _classify_skill_key(intent: str, summary: str) -> str | None:
    normalized_intent = _clean_token(intent)
    if normalized_intent in _INTENT_ALIASES:
        return _INTENT_ALIASES[normalized_intent]

    text = " ".join([normalized_intent, summary.lower()])
    if _has_any(text, ("event", "meetup", "meet up", "conference", "panel", "summit", "webinar")):
        return "event_planning"
    if _has_any(text, ("intro", "introduc", "connect", "network", "reach out", "follow up")):
        return "networking_intro"
    if _has_any(text, ("contact", "met", "meet", "name", "who is")):
        return "contact_capture"
    if _has_any(text, ("schedule", "calendar", "call", "meeting", "sync", "f2f")):
        return "coordination"
    if _has_any(text, ("stakeholder", "security", "risk", "compliance", "open source", "use case")):
        return "stakeholder_alignment"
    if _has_any(text, ("compare", "evaluate", "option", "decision", "trade-off", "tradeoff")):
        return "research_synthesis"
    if _has_any(text, ("frontend", "terminal", "cli", "tui", "ui", "ux")):
        return "frontend_terminal_build"
    return None


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _clip_summary(summary: str, limit: int = 96) -> str:
    clean = " ".join(summary.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."
