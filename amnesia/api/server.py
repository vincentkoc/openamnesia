"""OpenAmnesia API server — thin read-only layer over the SQLite store."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Resolve DB path relative to the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.environ.get("AMNESIA_DB", str(_PROJECT_ROOT / "data" / "amnesia.db"))

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA query_only=ON")
    return _conn


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        d: dict[str, Any] = dict(row)
        for key in list(d.keys()):
            if key.endswith("_json") and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        result.append(d)
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    _get_conn()
    yield
    if _conn:
        _conn.close()


app = FastAPI(title="OpenAmnesia", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Stats ────────────────────────────────────────────────────────────────────


@app.get("/api/stats")
def get_stats():
    conn = _get_conn()
    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    total_moments = conn.execute("SELECT COUNT(*) FROM moments").fetchone()[0]
    total_skills = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    total_entities = conn.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]

    sources = _rows_to_dicts(
        conn.execute(
            "SELECT source, COUNT(*) as event_count FROM events GROUP BY source"
        ).fetchall()
    )

    recent_events = conn.execute(
        "SELECT COUNT(*) FROM events WHERE ts >= datetime('now', '-24 hours')"
    ).fetchone()[0]

    return {
        "total_events": total_events,
        "total_sessions": total_sessions,
        "total_moments": total_moments,
        "total_skills": total_skills,
        "total_entities": total_entities,
        "recent_events_24h": recent_events,
        "sources": sources,
    }


# ── Events ───────────────────────────────────────────────────────────────────


@app.get("/api/events")
def list_events(
    source: str | None = None,
    session_id: str | None = None,
    actor: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    since: str | None = None,
    until: str | None = None,
):
    conn = _get_conn()
    clauses: list[str] = []
    params: list[Any] = []
    if source:
        clauses.append("source = ?")
        params.append(source)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if actor:
        clauses.append("actor = ?")
        params.append(actor)
    if since:
        clauses.append("ts >= ?")
        params.append(since)
    if until:
        clauses.append("ts <= ?")
        params.append(until)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM events {where} ORDER BY ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    total = conn.execute(f"SELECT COUNT(*) FROM events {where}", params[:-2]).fetchone()[0]

    return {"items": _rows_to_dicts(rows), "total": total, "limit": limit, "offset": offset}


# ── Sessions ─────────────────────────────────────────────────────────────────


@app.get("/api/sessions")
def list_sessions(
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    conn = _get_conn()
    clauses: list[str] = []
    params: list[Any] = []
    if source:
        clauses.append("s.source = ?")
        params.append(source)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT s.*,
            (SELECT COUNT(*) FROM events e WHERE e.session_id = s.session_id) as event_count,
            (SELECT COUNT(*) FROM moments m WHERE m.session_key = s.session_key) as moment_count
        FROM sessions s {where}
        ORDER BY s.start_ts DESC LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()

    total = conn.execute(f"SELECT COUNT(*) FROM sessions s {where}", params[:-2]).fetchone()[0]
    return {"items": _rows_to_dicts(rows), "total": total, "limit": limit, "offset": offset}


# ── Moments ──────────────────────────────────────────────────────────────────


@app.get("/api/moments")
def list_moments(
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    conn = _get_conn()
    clauses: list[str] = []
    params: list[Any] = []
    if source:
        clauses.append("s.source = ?")
        params.append(source)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT m.*, s.source, s.start_ts as session_start_ts, s.end_ts as session_end_ts
        FROM moments m
        JOIN sessions s ON m.session_key = s.session_key
        {where}
        ORDER BY s.start_ts DESC, m.start_turn ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()

    total = conn.execute(
        f"SELECT COUNT(*) FROM moments m JOIN sessions s ON m.session_key = s.session_key {where}",
        params[:-2],
    ).fetchone()[0]
    return {"items": _rows_to_dicts(rows), "total": total, "limit": limit, "offset": offset}


@app.get("/api/moments/{moment_id}")
def get_moment(moment_id: str):
    conn = _get_conn()
    moment = conn.execute(
        """
        SELECT m.*, s.source,
               s.start_ts as session_start_ts,
               s.end_ts as session_end_ts,
               s.summary as session_summary
        FROM moments m
        JOIN sessions s ON m.session_key = s.session_key
        WHERE m.moment_id = ?
        """,
        (moment_id,),
    ).fetchone()
    if not moment:
        return {"error": "not found"}, 404

    events = conn.execute(
        """
        SELECT * FROM events
        WHERE session_id = (SELECT session_id FROM sessions WHERE session_key = ?)
        AND turn_index BETWEEN ? AND ?
        ORDER BY turn_index ASC
        """,
        (moment["session_key"], moment["start_turn"], moment["end_turn"]),
    ).fetchall()

    result = dict(moment)
    for key in list(result.keys()):
        if key.endswith("_json") and isinstance(result[key], str):
            try:
                result[key] = json.loads(result[key])
            except (json.JSONDecodeError, TypeError):
                pass
    result["events"] = _rows_to_dicts(events)
    return result


# ── Skills ───────────────────────────────────────────────────────────────────


@app.get("/api/skills")
def list_skills(
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    conn = _get_conn()
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM skills {where} ORDER BY updated_ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()

    total = conn.execute(f"SELECT COUNT(*) FROM skills {where}", params[:-2]).fetchone()[0]
    return {"items": _rows_to_dicts(rows), "total": total, "limit": limit, "offset": offset}


@app.get("/api/skills/{skill_id}")
def get_skill(skill_id: str):
    conn = _get_conn()
    skill = conn.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,)).fetchone()
    if not skill:
        return {"error": "not found"}, 404

    evals = conn.execute(
        "SELECT * FROM skill_evals WHERE skill_id = ? ORDER BY ts DESC", (skill_id,)
    ).fetchall()
    patches = conn.execute(
        "SELECT * FROM skill_patches WHERE skill_id = ? ORDER BY ts DESC", (skill_id,)
    ).fetchall()

    result = dict(skill)
    for key in list(result.keys()):
        if key.endswith("_json") and isinstance(result[key], str):
            try:
                result[key] = json.loads(result[key])
            except (json.JSONDecodeError, TypeError):
                pass
    result["evals"] = _rows_to_dicts(evals)
    result["patches"] = _rows_to_dicts(patches)
    return result


# ── Sources ──────────────────────────────────────────────────────────────────


@app.get("/api/sources")
def list_sources():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM source_status ORDER BY source").fetchall()
    return {"items": _rows_to_dicts(rows)}


# ── Timeline ─────────────────────────────────────────────────────────────────


@app.get("/api/timeline")
def get_timeline(
    granularity: str = Query(default="hour", pattern="^(hour|day|week)$"),
    since: str | None = None,
    until: str | None = None,
):
    conn = _get_conn()

    if granularity == "hour":
        bucket_expr = "strftime('%Y-%m-%dT%H:00:00', ts)"
    elif granularity == "day":
        bucket_expr = "strftime('%Y-%m-%d', ts)"
    else:
        bucket_expr = "strftime('%Y-%W', ts)"

    clauses: list[str] = []
    params: list[Any] = []
    if since:
        clauses.append("ts >= ?")
        params.append(since)
    if until:
        clauses.append("ts <= ?")
        params.append(until)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT {bucket_expr} as bucket, source, COUNT(*) as event_count,
            SUM(CASE WHEN tool_status = 'error' THEN 1 ELSE 0 END) as error_count,
            COUNT(DISTINCT session_id) as session_count
        FROM events {where}
        GROUP BY bucket, source
        ORDER BY bucket ASC
    """
    rows = conn.execute(sql, params).fetchall()
    return {"items": _rows_to_dicts(rows)}


# ── Entities ─────────────────────────────────────────────────────────────────


@app.get("/api/entities")
def list_entities(
    entity_type: str | None = None,
    limit: int = Query(default=50, le=200),
):
    conn = _get_conn()
    clauses: list[str] = []
    params: list[Any] = []
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT entity_type, entity_value, COUNT(*) as mention_count,
            AVG(confidence) as avg_confidence,
            MIN(ts) as first_seen, MAX(ts) as last_seen
        FROM entity_mentions {where}
        GROUP BY entity_type, entity_value
        ORDER BY mention_count DESC
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return {"items": _rows_to_dicts(rows)}


# ── Ingest Audit ─────────────────────────────────────────────────────────────


@app.get("/api/audit")
def list_audit(limit: int = Query(default=20, le=100)):
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM ingest_audit ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return {"items": _rows_to_dicts(rows)}


# ── Static files (serve built frontend) ─────────────────────────────────────

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
