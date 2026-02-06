from __future__ import annotations

from amnesia.models import Moment, Session


def momentize_sessions(sessions: list[Session]) -> list[Moment]:
    moments: list[Moment] = []

    for session in sessions:
        moment_id = f"{session.session_key}:0"
        moments.append(
            Moment(
                moment_id=moment_id,
                session_key=session.session_key,
                start_turn=0,
                end_turn=max(int(session.meta_json.get("event_count", 1)) - 1, 0),
                intent="unknown",
                outcome="partial",
                friction_score=0.0,
                summary=session.summary,
                evidence_json={
                    "session_id": session.session_id,
                    "day_ts": session.start_ts.isoformat(),
                },
                artifacts_json={"count": 0},
            )
        )

    return moments
