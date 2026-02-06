from __future__ import annotations

from collections import defaultdict

from amnesia.models import Event, Session


def sessionize_events(events: list[Event]) -> list[Session]:
    grouped: dict[tuple[str, str], list[Event]] = defaultdict(list)

    for event in events:
        grouped[(event.source, event.session_id)].append(event)

    sessions: list[Session] = []
    for (source, session_id), session_events in grouped.items():
        ordered = sorted(session_events, key=lambda item: (item.ts, item.turn_index))
        start = ordered[0].ts
        end = ordered[-1].ts
        summary = ordered[0].content[:160]

        sessions.append(
            Session(
                session_key=session_id,
                session_id=session_id,
                source=source,
                start_ts=start,
                end_ts=end,
                summary=summary,
                meta_json={"event_count": len(ordered)},
            )
        )

    return sessions
