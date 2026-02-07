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


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "for",
    "from",
    "had",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "so",
    "that",
    "the",
    "their",
    "then",
    "they",
    "this",
    "to",
    "up",
    "we",
    "with",
    "you",
    "your",
    "cluster",
    "clusters",
    "event",
    "events",
    "appears",
    "appeared",
    "summary",
    "workflow",
    "workflows",
    "task",
    "tasks",
    "tool_output",
    "tool_result",
    "exec_command",
}

_ACTION_PHRASES = [
    "follow up",
    "reach out",
    "set up",
    "check in",
    "sync up",
]

_ACTION_VERBS = [
    "plan",
    "schedule",
    "coordinate",
    "connect",
    "introduce",
    "research",
    "evaluate",
    "compare",
    "design",
    "build",
    "implement",
    "ship",
    "deploy",
    "debug",
    "fix",
    "review",
    "draft",
    "write",
    "update",
    "refactor",
    "summarize",
    "track",
    "follow",
]

_ACTION_STEPS = {
    "plan": [
        "capture goals and constraints",
        "identify stakeholders and timing",
        "outline next actions and deadlines",
    ],
    "schedule": [
        "propose time windows",
        "confirm availability",
        "send invite and reminders",
    ],
    "coordinate": [
        "align on objectives",
        "assign owners and next steps",
        "track follow-ups",
    ],
    "connect": [
        "identify the parties",
        "collect context and desired outcome",
        "draft the intro and follow-up",
    ],
    "introduce": [
        "identify the parties",
        "collect context and desired outcome",
        "draft the intro and follow-up",
    ],
    "research": [
        "collect sources and constraints",
        "compare options and trade-offs",
        "summarize recommendations",
    ],
    "evaluate": [
        "list evaluation criteria",
        "compare options",
        "record decision and next step",
    ],
    "design": [
        "define interaction goal",
        "sketch flow and edge cases",
        "validate with quick prototype",
    ],
    "build": [
        "define scope and success criteria",
        "implement the workflow",
        "validate output and iterate",
    ],
    "deploy": [
        "prepare release checklist",
        "ship and verify",
        "monitor for regressions",
    ],
    "debug": [
        "reproduce the issue",
        "inspect logs and traces",
        "apply fix and verify",
    ],
    "fix": [
        "identify root cause",
        "apply fix",
        "verify behavior",
    ],
    "review": [
        "gather context",
        "review for gaps",
        "record outcomes and next steps",
    ],
    "draft": [
        "collect required inputs",
        "draft the artifact",
        "review and finalize",
    ],
    "write": [
        "collect required inputs",
        "draft the artifact",
        "review and finalize",
    ],
    "update": [
        "identify changes",
        "apply updates",
        "confirm correctness",
    ],
    "summarize": [
        "collect key points",
        "write concise summary",
        "capture next actions",
    ],
    "track": [
        "log the current state",
        "set reminders or checkpoints",
        "capture outcome",
    ],
    "follow up": [
        "confirm the ask",
        "send reminder",
        "log the outcome",
    ],
}

_TITLE_OVERRIDES = {
    "ai": "AI",
    "api": "API",
    "llm": "LLM",
    "ml": "ML",
    "mlops": "MLOps",
    "ui": "UI",
    "ux": "UX",
    "gpt": "GPT",
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
        summary = enrichment.summary or ""
        low_signal = _is_low_signal_summary(summary)
        if low_signal:
            summary = ""

        fact_candidates.append(
            {
                "kind": "cluster_summary",
                "cluster_id": enrichment.cluster_id,
                "summary": summary or enrichment.summary,
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
            if not low_signal:
                intent = _infer_intent_from_summary(summary or enrichment.summary)
            else:
                intent = ""
        if intent and not low_signal:
            skill_seed.append(
                SkillSeed(
                    intent=intent,
                    summary=summary or "",
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
    action_samples: dict[str, str] = {}
    topic_samples: dict[str, list[str]] = {}

    for seed in skill_seed:
        action = _extract_action(seed.intent, seed.summary)
        topics = _extract_topics(seed.intent, seed.summary, action)
        skill_key = _build_skill_key(action, topics)
        if not skill_key or not topics:
            continue
        count_by_key[skill_key] += 1
        confidence_sum[skill_key] = confidence_sum.get(skill_key, 0.0) + seed.confidence
        support_sum[skill_key] = support_sum.get(skill_key, 0) + seed.support
        intent_samples.setdefault(skill_key, []).append(seed.intent)
        summary_samples.setdefault(skill_key, []).append(seed.summary)
        action_samples[skill_key] = action
        topic_samples.setdefault(skill_key, []).extend(topics)

    candidates: list[dict[str, Any]] = []
    for skill_key, freq in count_by_key.most_common():
        action = action_samples.get(skill_key, "track")
        topics = _top_topics(topic_samples.get(skill_key, []))
        avg_conf = confidence_sum[skill_key] / max(1, freq)
        total_support = support_sum[skill_key]
        sample_intents = sorted(set(intent_samples.get(skill_key, [])))[:3]
        sample_summaries = [
            _clip_summary(summary) for summary in summary_samples.get(skill_key, [])[:2]
        ]
        composio_toolkits = _suggest_composio_toolkits(
            " ".join(sample_summaries + sample_intents + topics + [action])
        )
        name = _format_skill_name(action, topics)
        steps = _ACTION_STEPS.get(action, _ACTION_STEPS["track"])
        checks = _build_checks(action, topics)
        candidates.append(
            {
                "name": name,
                "trigger": {
                    "action": action,
                    "topics": topics,
                    "sample_intents": sample_intents,
                },
                "steps": steps,
                "checks": checks,
                "composio": {"toolkits": composio_toolkits},
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
    if "follow up" in low or "reach out" in low or "connect" in low:
        return "follow up"
    for verb in _ACTION_VERBS:
        if verb in low:
            return verb
    return "track"


def _extract_action(intent: str, summary: str) -> str:
    text = f"{intent} {summary}".lower()
    for phrase in _ACTION_PHRASES:
        if phrase in text:
            return phrase
    for verb in _ACTION_VERBS:
        if re.search(rf"\\b{re.escape(verb)}\\b", text):
            return verb
    return "track"


def _extract_topics(intent: str, summary: str, action: str) -> list[str]:
    text = f"{intent} {summary}".lower()
    cleaned = re.sub(r"[^a-z0-9_\\s-]+", " ", text)
    tokens = [token.strip("-_") for token in cleaned.split() if token.strip("-_")]
    action_tokens = set(action.split())
    topics = []
    for token in tokens:
        if token in _STOPWORDS or token in action_tokens or len(token) <= 2:
            continue
        if token.isdigit():
            continue
        if _looks_like_id(token):
            continue
        topics.append(token)
    return topics[:12]


def _build_skill_key(action: str, topics: list[str]) -> str | None:
    if not action or not topics:
        return None
    if len(topics) < 2:
        return None
    key = f"{action}:{' '.join(topics[:3])}"
    return key[:120]


def _top_topics(topics: list[str], limit: int = 4) -> list[str]:
    if not topics:
        return []
    counts = Counter(topics)
    return [item for item, _count in counts.most_common(limit)]


def _format_skill_name(action: str, topics: list[str]) -> str:
    action_label = _title_token(action)
    if not topics:
        return f"Task: {action_label}"
    topic_label = " ".join(_title_token(topic) for topic in topics[:3])
    return f"Task: {action_label} {topic_label}"


def _title_token(token: str) -> str:
    if token in _TITLE_OVERRIDES:
        return _TITLE_OVERRIDES[token]
    return token.replace("_", " ").title()


def _build_checks(action: str, topics: list[str]) -> list[str]:
    checks = ["context_present", "next_action_present"]
    joined = " ".join(topics).lower()
    if any(term in joined for term in ("meeting", "calendar", "schedule", "invite", "call")):
        checks.append("time_reference_present")
    if action in {"connect", "introduce", "follow up"}:
        checks.append("contacts_present")
    return list(dict.fromkeys(checks))


def _looks_like_id(token: str) -> bool:
    if len(token) >= 16 and re.fullmatch(r"[a-f0-9]+", token):
        return True
    if len(token) >= 20 and re.fullmatch(r"[a-z0-9]+", token):
        return True
    return False


def _is_low_signal_summary(summary: str) -> bool:
    if not summary:
        return True
    low = summary.lower().strip()
    if low.startswith("cluster ") and "appears" in low:
        return True
    if any(term in low for term in ("tool_output", "tool_result", "exec_command")):
        return True
    return False


def _clip_summary(summary: str, limit: int = 96) -> str:
    clean = " ".join(summary.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _suggest_composio_toolkits(text: str) -> list[str]:
    low = text.lower()
    toolkits: list[str] = []
    if any(term in low for term in ("issue", "repo", "pull request", "merge", "github")):
        toolkits.append("github")
    if any(term in low for term in ("email", "inbox", "gmail", "send mail")):
        toolkits.append("gmail")
    if any(term in low for term in ("doc", "notion", "wiki", "spec")):
        toolkits.append("notion")
    if any(term in low for term in ("calendar", "meeting", "schedule", "invite")):
        toolkits.append("google_calendar")
    if any(term in low for term in ("slack", "channel", "message")):
        toolkits.append("slack")
    return list(dict.fromkeys(toolkits))[:5]
