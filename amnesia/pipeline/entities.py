"""Deterministic entity extraction for people, places, and projects."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from amnesia.models import EntityMention, EntityRollup, Event

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\+?\d[\d\-\s()]{8,}\d")
PROJECT_RE = re.compile(
    (
        r"(?:\bproject\s+([A-Za-z0-9._-]{2,})\b)"
        r"|(?:\b([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)\b)"
        r"|(?:#([A-Za-z0-9._-]{2,}))"
    ),
    re.IGNORECASE,
)

PLACE_TERMS = {
    "london",
    "sydney",
    "melbourne",
    "new york",
    "san francisco",
    "singapore",
    "tokyo",
    "rise",
    "barclays",
}


@dataclass(slots=True)
class EntityExtractionResult:
    mentions: list[EntityMention]
    rollups: list[EntityRollup]


def extract_entities(events: list[Event], *, granularity: str = "week") -> EntityExtractionResult:
    mentions: list[EntityMention] = []
    for event in events:
        mentions.extend(_extract_from_event(event))
    rollups = build_entity_rollups(mentions, granularity=granularity)
    return EntityExtractionResult(mentions=mentions, rollups=rollups)


def build_entity_rollups(
    mentions: list[EntityMention], *, granularity: str = "week"
) -> list[EntityRollup]:
    counter: Counter[tuple[str, str, str, datetime]] = Counter()
    for mention in mentions:
        bucket = _bucket_start(mention.ts, granularity)
        key = (mention.source, mention.entity_type, mention.entity_value, bucket)
        counter[key] += 1

    rollups: list[EntityRollup] = []
    for (source, entity_type, entity_value, bucket), count in counter.items():
        rollup_id = _stable_id(
            f"{source}|{entity_type}|{entity_value}|{granularity}|{bucket.isoformat()}"
        )
        rollups.append(
            EntityRollup(
                rollup_id=rollup_id,
                bucket_start_ts=bucket,
                bucket_granularity=granularity,
                source=source,
                entity_type=entity_type,
                entity_value=entity_value,
                mention_count=count,
                meta_json={},
            )
        )
    rollups.sort(key=lambda item: (item.bucket_start_ts, item.mention_count), reverse=True)
    return rollups


def _extract_from_event(event: Event) -> list[EntityMention]:
    mentions: list[EntityMention] = []
    text = event.content

    for email in EMAIL_RE.findall(text):
        mentions.append(_make_mention(event, "person", email.lower(), confidence=0.98))

    for phone in PHONE_RE.findall(text):
        # Avoid treating short numeric fragments (dates/order ids) as people.
        if "+" not in phone and not any(ch in phone for ch in (" ", "-", "(", ")")):
            continue
        normalized = re.sub(r"\D+", "", phone)
        if 10 <= len(normalized) <= 15:
            mentions.append(_make_mention(event, "person", normalized, confidence=0.90))

    low = text.lower()
    for place in PLACE_TERMS:
        if place in low:
            mentions.append(_make_mention(event, "place", place, confidence=0.70))

    for match in PROJECT_RE.finditer(text):
        project = next((group for group in match.groups() if group), None)
        if project is None:
            continue
        low_project = project.lower()
        if low_project.startswith("http") or "." in low_project:
            continue
        mentions.append(_make_mention(event, "project", project, confidence=0.75))

    # dedupe within event
    unique: dict[tuple[str, str], EntityMention] = {}
    for mention in mentions:
        unique[(mention.entity_type, mention.entity_value)] = mention
    return list(unique.values())


def _make_mention(
    event: Event,
    entity_type: str,
    entity_value: str,
    confidence: float,
) -> EntityMention:
    mention_id = _stable_id(f"{event.event_id}|{entity_type}|{entity_value}")
    ts = event.ts.astimezone(UTC)
    return EntityMention(
        mention_id=mention_id,
        event_id=event.event_id,
        ts=ts,
        source=event.source,
        entity_type=entity_type,
        entity_value=entity_value,
        confidence=confidence,
        meta_json={},
    )


def _bucket_start(ts: datetime, granularity: str) -> datetime:
    utc = ts.astimezone(UTC)
    if granularity == "day":
        return utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "month":
        return utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # week default: monday-based
    day_start = utc.replace(hour=0, minute=0, second=0, microsecond=0)
    delta_days = day_start.weekday()
    return day_start - timedelta(days=delta_days)


def _stable_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()
