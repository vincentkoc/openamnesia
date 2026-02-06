from __future__ import annotations

from collections import Counter

from amnesia.models import Moment


def mine_skill_candidates(moments: list[Moment]) -> list[dict]:
    counts = Counter(moment.intent for moment in moments)
    candidates: list[dict] = []

    for intent, count in counts.items():
        if count < 2:
            continue
        related = [m for m in moments if m.intent == intent]
        success_rate = sum(1 for m in related if m.outcome == "success") / max(len(related), 1)
        avg_turns = sum((m.end_turn - m.start_turn + 1) for m in related) / max(len(related), 1)
        candidates.append(
            {
                "name": intent,
                "trigger": {"intent": intent},
                "steps": ["collect evidence", "summarize", "publish"],
                "checks": ["outcome present", "artifacts present"],
                "metrics": {
                    "support": count,
                    "success_rate": round(success_rate, 3),
                    "avg_turns": round(avg_turns, 2),
                },
            }
        )

    return candidates
