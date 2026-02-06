from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from amnesia.models import Event, IngestAudit, Moment, Session, SourceStatus, utc_now


class SQLiteStore:
    def __init__(self, dsn: str):
        self.db_path = self._extract_path(dsn)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        self.conn.executescript(schema)
        self.conn.commit()

    def save_events(self, events: list[Event]) -> int:
        inserted = 0
        for event in events:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, ts, source, session_id, turn_index, actor, content,
                    tool_name, tool_status, tool_args_json, tool_result_json, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.ts.astimezone(UTC).isoformat(),
                    event.source,
                    event.session_id,
                    event.turn_index,
                    event.actor,
                    event.content,
                    event.tool_name,
                    event.tool_status,
                    to_json(event.tool_args_json),
                    to_json(event.tool_result_json),
                    to_json(event.meta_json),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def save_sessions(self, sessions: list[Session]) -> int:
        inserted = 0
        for session in sessions:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO sessions (
                    session_key, session_id, source, start_ts, end_ts, summary, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_key,
                    session.session_id,
                    session.source,
                    session.start_ts.isoformat(),
                    session.end_ts.isoformat(),
                    session.summary,
                    to_json(session.meta_json),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def save_moments(self, moments: list[Moment]) -> int:
        inserted = 0
        for moment in moments:
            cur = self.conn.execute(
                """
                INSERT OR IGNORE INTO moments (
                    moment_id, session_key, start_turn, end_turn, intent, outcome,
                    friction_score, summary, evidence_json, artifacts_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    moment.moment_id,
                    moment.session_key,
                    moment.start_turn,
                    moment.end_turn,
                    moment.intent,
                    moment.outcome,
                    moment.friction_score,
                    moment.summary,
                    to_json(moment.evidence_json),
                    to_json(moment.artifacts_json),
                ),
            )
            inserted += cur.rowcount
        self.conn.commit()
        return inserted

    def save_skill_candidates(self, skills: list[dict]) -> int:
        inserted = 0
        now = utc_now().isoformat()
        for skill in skills:
            skill_id = str(uuid.uuid4())
            cur = self.conn.execute(
                """
                INSERT INTO skills (
                    skill_id, name, trigger_json, steps_json, checks_json,
                    version, status, metrics_json, created_ts, updated_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name, version) DO UPDATE SET
                  trigger_json=excluded.trigger_json,
                  steps_json=excluded.steps_json,
                  checks_json=excluded.checks_json,
                  metrics_json=excluded.metrics_json,
                  updated_ts=excluded.updated_ts
                """,
                (
                    skill_id,
                    skill.get("name", "unknown"),
                    to_json(skill.get("trigger")),
                    to_json(skill.get("steps")),
                    to_json(skill.get("checks")),
                    "v0",
                    "candidate",
                    to_json(skill.get("metrics")),
                    now,
                    now,
                ),
            )
            inserted += int(cur.rowcount > 0)
        self.conn.commit()
        return inserted

    def save_source_status(self, status: SourceStatus) -> None:
        self.conn.execute(
            """
            INSERT INTO source_status (
                source, status, last_poll_ts, records_seen, records_ingested, error_message
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
              status=excluded.status,
              last_poll_ts=excluded.last_poll_ts,
              records_seen=excluded.records_seen,
              records_ingested=excluded.records_ingested,
              error_message=excluded.error_message
            """,
            (
                status.source,
                status.status,
                status.last_poll_ts.isoformat(),
                status.records_seen,
                status.records_ingested,
                status.error_message,
            ),
        )
        self.conn.commit()

    def list_source_status(self) -> list[SourceStatus]:
        rows = self.conn.execute(
            """
            SELECT source, status, last_poll_ts, records_seen, records_ingested, error_message
            FROM source_status
            ORDER BY source
            """
        ).fetchall()
        statuses: list[SourceStatus] = []
        for row in rows:
            statuses.append(
                SourceStatus(
                    source=row["source"],
                    status=row["status"],
                    last_poll_ts=datetime.fromisoformat(row["last_poll_ts"]),
                    records_seen=row["records_seen"],
                    records_ingested=row["records_ingested"],
                    error_message=row["error_message"],
                )
            )
        return statuses

    def append_ingest_audit(self, audit: IngestAudit) -> None:
        self.conn.execute(
            """
            INSERT INTO ingest_audit (
                audit_id, ts, source, event_count, session_count, moment_count,
                skill_count, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit.audit_id,
                audit.ts.isoformat(),
                audit.source,
                audit.event_count,
                audit.session_count,
                audit.moment_count,
                audit.skill_count,
                to_json(audit.details_json),
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _extract_path(dsn: str) -> str:
        if not dsn.startswith("sqlite:///"):
            raise ValueError(f"Unsupported sqlite dsn: {dsn}")
        return dsn.removeprefix("sqlite:///")


def to_json(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True)
