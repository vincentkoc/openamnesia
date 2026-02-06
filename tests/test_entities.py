from __future__ import annotations

from datetime import UTC, datetime

from amnesia.models import Event
from amnesia.pipeline.entities import extract_entities


def test_extract_entities_people_places_projects() -> None:
    event = Event(
        event_id="e1",
        ts=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
        source="imessage",
        session_id="s1",
        turn_index=0,
        actor="me",
        content=(
            "Talk to lauren.batten@icloud.com and +1 (650) 444-7144 about "
            "project openamnesia in London and repo comet-ml/opik."
        ),
    )
    result = extract_entities([event], granularity="week")

    kinds = {(mention.entity_type, mention.entity_value) for mention in result.mentions}
    assert ("person", "lauren.batten@icloud.com") in kinds
    assert ("person", "16504447144") in kinds
    assert ("place", "london") in kinds
    assert ("project", "openamnesia") in kinds or ("project", "comet-ml/opik") in kinds
    assert len(result.rollups) >= 1
