from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from amnesia.models import (
    ClusterEnrichment,
    ClusterMembership,
    EntityMention,
    EntityRollup,
    Event,
    EventCluster,
    EventEmbedding,
    IngestAudit,
    Moment,
    Session,
    SourceStatus,
    utc_now,
)


class SQLiteStore:
    def __init__(self, dsn: str):
        self.db_path = _extract_path(dsn)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA foreign_keys=OFF")

    def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        self.conn.executescript(schema)
        self.conn.commit()

    def save_events(self, events: list[Event]) -> int:
        if not events:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO events (
                event_id, ts, source, session_id, turn_index, actor, content,
                tool_name, tool_status, tool_args_json, tool_result_json, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
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
                )
                for event in events
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def save_sessions(self, sessions: list[Session]) -> int:
        if not sessions:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO sessions (
                session_key, session_id, source, start_ts, end_ts, summary, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    session.session_key,
                    session.session_id,
                    session.source,
                    session.start_ts.isoformat(),
                    session.end_ts.isoformat(),
                    session.summary,
                    to_json(session.meta_json),
                )
                for session in sessions
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def save_moments(self, moments: list[Moment]) -> int:
        if not moments:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO moments (
                moment_id, session_key, start_turn, end_turn, intent, outcome,
                friction_score, summary, evidence_json, artifacts_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
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
                )
                for moment in moments
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

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

    def save_entity_mentions(self, mentions: list[EntityMention]) -> int:
        if not mentions:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO entity_mentions (
                mention_id, event_id, ts, source, entity_type, entity_value, confidence, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    mention.mention_id,
                    mention.event_id,
                    mention.ts.astimezone(UTC).isoformat(),
                    mention.source,
                    mention.entity_type,
                    mention.entity_value,
                    mention.confidence,
                    to_json(mention.meta_json),
                )
                for mention in mentions
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def save_entity_rollups(self, rollups: list[EntityRollup]) -> int:
        if not rollups:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO entity_rollups (
                rollup_id, bucket_start_ts, bucket_granularity, source, entity_type,
                entity_value, mention_count, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    rollup.rollup_id,
                    rollup.bucket_start_ts.astimezone(UTC).isoformat(),
                    rollup.bucket_granularity,
                    rollup.source,
                    rollup.entity_type,
                    rollup.entity_value,
                    rollup.mention_count,
                    to_json(rollup.meta_json),
                )
                for rollup in rollups
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def close(self) -> None:
        self.conn.close()

    def save_event_embeddings(self, embeddings: list[EventEmbedding]) -> int:
        if not embeddings:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO event_embeddings (
                embedding_id, event_id, ts, source, model, vector_json, text_hash, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.embedding_id,
                    item.event_id,
                    item.ts.astimezone(UTC).isoformat(),
                    item.source,
                    item.model,
                    to_json(item.vector_json),
                    item.text_hash,
                    to_json(item.meta_json),
                )
                for item in embeddings
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def save_event_clusters(self, clusters: list[EventCluster]) -> int:
        if not clusters:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO event_clusters (
                cluster_id, ts, source, algorithm, label, size, centroid_json, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.cluster_id,
                    item.ts.astimezone(UTC).isoformat(),
                    item.source,
                    item.algorithm,
                    item.label,
                    item.size,
                    to_json(item.centroid_json),
                    to_json(item.meta_json),
                )
                for item in clusters
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def save_cluster_memberships(self, memberships: list[ClusterMembership]) -> int:
        if not memberships:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO cluster_memberships (
                membership_id, cluster_id, event_id, distance, ts, source, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.membership_id,
                    item.cluster_id,
                    item.event_id,
                    item.distance,
                    item.ts.astimezone(UTC).isoformat(),
                    item.source,
                    to_json(item.meta_json),
                )
                for item in memberships
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def save_cluster_enrichments(self, enrichments: list[ClusterEnrichment]) -> int:
        if not enrichments:
            return 0
        before = self.conn.total_changes
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO cluster_enrichments (
                enrichment_id, cluster_id, ts, source, provider, summary, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.enrichment_id,
                    item.cluster_id,
                    item.ts.astimezone(UTC).isoformat(),
                    item.source,
                    item.provider,
                    item.summary,
                    to_json(item.payload_json),
                )
                for item in enrichments
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def list_events_for_source(
        self,
        *,
        source: str,
        since_ts: str | None = None,
        limit: int = 5000,
    ) -> list[Event]:
        normalized_since = _normalize_since_ts(since_ts)
        params: list[object] = [source]
        where = "source = ?"
        if normalized_since:
            where += " AND ts >= ?"
            params.append(normalized_since)
        params.append(max(0, limit))
        rows = self.conn.execute(
            f"""
            SELECT event_id, ts, source, session_id, turn_index, actor, content,
                   tool_name, tool_status, tool_args_json, tool_result_json, meta_json
            FROM events
            WHERE {where}
            ORDER BY ts DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()

        events: list[Event] = []
        for row in rows:
            events.append(
                Event(
                    event_id=row["event_id"],
                    ts=_parse_event_ts(row["ts"]),
                    source=row["source"],
                    session_id=row["session_id"],
                    turn_index=int(row["turn_index"]),
                    actor=row["actor"],
                    content=row["content"],
                    tool_name=row["tool_name"],
                    tool_status=row["tool_status"],
                    tool_args_json=from_json(row["tool_args_json"]),
                    tool_result_json=from_json(row["tool_result_json"]),
                    meta_json=from_json(row["meta_json"]) or {},
                )
            )
        return events


def _normalize_since_ts(since_ts: str | None) -> str | None:
    if since_ts is None or not str(since_ts).strip():
        return None
    raw = str(since_ts).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds")


def _parse_event_ts(value: str) -> datetime:
    raw = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _extract_path(dsn: str) -> str:
    if not dsn.startswith("sqlite:///"):
        raise ValueError(f"Unsupported sqlite dsn: {dsn}")
    return dsn.removeprefix("sqlite:///")


def to_json(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True)


def from_json(value: str | None) -> object | None:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
