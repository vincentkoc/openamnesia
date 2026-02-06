from __future__ import annotations

from amnesia.models import Event, Moment


def annotate_moments(moments: list[Moment], events: list[Event]) -> list[Moment]:
    by_session: dict[str, list[Event]] = {}
    for event in events:
        by_session.setdefault(event.session_id, []).append(event)

    for moment in moments:
        session_events = by_session.get(moment.session_key, [])
        content = " ".join(e.content.lower() for e in session_events[:8])

        if "error" in content or "failed" in content:
            moment.outcome = "fail"
            moment.friction_score = 0.8
        elif "done" in content or "success" in content:
            moment.outcome = "success"
            moment.friction_score = 0.2
        else:
            moment.outcome = "partial"
            moment.friction_score = 0.5

        moment.intent = infer_intent(content)
        moment.artifacts_json = {
            "commands": [e.content for e in session_events if e.source == "terminal"][:5],
            "count": len(session_events),
        }

    return moments


def infer_intent(content: str) -> str:
    if "release" in content or "changelog" in content:
        return "release_notes"
    if "test" in content or "failing" in content:
        return "debug_and_fix"
    if "refactor" in content:
        return "refactor"
    return "general_task"
