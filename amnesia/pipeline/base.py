from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from amnesia.models import Event, Moment, Session


@dataclass(slots=True)
class PipelineContext:
    events: list[Event] = field(default_factory=list)
    sessions: list[Session] = field(default_factory=list)
    moments: list[Moment] = field(default_factory=list)
    derived: dict[str, Any] = field(default_factory=dict)


class PipelineHook:
    def run(self, ctx: PipelineContext) -> PipelineContext:
        return ctx
