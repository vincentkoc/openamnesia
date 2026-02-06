from __future__ import annotations

from dataclasses import dataclass, field

from amnesia.models import Event, IngestAudit, Moment, Session, SourceStatus


@dataclass(slots=True)
class InMemoryStore:
    events: dict[str, Event] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)
    moments: dict[str, Moment] = field(default_factory=dict)
    skills: dict[str, dict] = field(default_factory=dict)
    source_status: dict[str, SourceStatus] = field(default_factory=dict)
    audits: list[IngestAudit] = field(default_factory=list)

    def init_schema(self) -> None:
        return

    def save_events(self, events: list[Event]) -> int:
        inserted = 0
        for event in events:
            if event.event_id not in self.events:
                self.events[event.event_id] = event
                inserted += 1
        return inserted

    def save_sessions(self, sessions: list[Session]) -> int:
        inserted = 0
        for session in sessions:
            if session.session_key not in self.sessions:
                self.sessions[session.session_key] = session
                inserted += 1
        return inserted

    def save_moments(self, moments: list[Moment]) -> int:
        inserted = 0
        for moment in moments:
            if moment.moment_id not in self.moments:
                self.moments[moment.moment_id] = moment
                inserted += 1
        return inserted

    def save_skill_candidates(self, skills: list[dict]) -> int:
        inserted = 0
        for skill in skills:
            key = f"{skill['name']}:v0"
            if key not in self.skills:
                inserted += 1
            self.skills[key] = skill
        return inserted

    def save_source_status(self, status: SourceStatus) -> None:
        self.source_status[status.source] = status

    def list_source_status(self) -> list[SourceStatus]:
        return sorted(self.source_status.values(), key=lambda item: item.source)

    def append_ingest_audit(self, audit: IngestAudit) -> None:
        self.audits.append(audit)

    def close(self) -> None:
        return
