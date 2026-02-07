"""OpenAmnesia API server — thin read-only layer over the SQLite store."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from amnesia.api.memory import router as memory_router
from amnesia.config import StoreConfig
from amnesia.store.factory import build_store

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
app.include_router(memory_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "PATCH"],
    allow_headers=["*"],
)


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("uvicorn is required to run the API server") from exc
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()


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


class SkillStatusUpdate(BaseModel):
    status: str  # candidate, validated, promoted, rejected


@app.patch("/api/skills/{skill_id}")
def update_skill(skill_id: str, body: SkillStatusUpdate):
    allowed = {"candidate", "validated", "promoted", "rejected"}
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(f"Invalid status. Must be one of: {', '.join(sorted(allowed))}"),
        )
    store = build_store(StoreConfig(backend="sqlite", dsn=f"sqlite:///{DB_PATH}"))
    try:
        updated = store.update_skill_status(skill_id, body.status)
    finally:
        store.close()
    if not updated:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"ok": True, "skill_id": skill_id, "status": body.status}


# ── Sources ──────────────────────────────────────────────────────────────────


def _compute_heartbeat(conn: sqlite3.Connection, source: str, points: int = 60) -> list[int]:
    """Compute a heartbeat array: event counts in recent 5-min buckets, normalized 0-100."""
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m-%dT%H:', ts)
               || printf('%02d', (CAST(strftime('%M', ts) AS INT) / 5) * 5)
               as bucket,
               COUNT(*) as cnt
        FROM events
        WHERE source = ? AND ts >= datetime('now', '-5 hours')
        GROUP BY bucket ORDER BY bucket ASC
        """,
        (source,),
    ).fetchall()
    counts = [r["cnt"] for r in rows]
    if not counts:
        return [0] * points
    mx = max(counts) or 1
    normalized = [min(100, round((c / mx) * 100)) for c in counts]
    # Pad/trim to desired length
    if len(normalized) >= points:
        return normalized[-points:]
    return [0] * (points - len(normalized)) + normalized


@app.get("/api/sources")
def list_sources():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM source_status ORDER BY source").fetchall()
    items = _rows_to_dicts(rows)
    for item in items:
        item["heartbeat"] = _compute_heartbeat(conn, item["source"])
    return {"items": items}


@app.get("/api/sources/{source}/diagnostics")
def get_source_diagnostics(source: str):
    conn = _get_conn()
    # Verify source exists
    row = conn.execute("SELECT * FROM source_status WHERE source = ?", (source,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")

    heartbeat = _compute_heartbeat(conn, source, 120)

    # Stats: compute from recent events
    stats_row = conn.execute(
        """
        SELECT COUNT(*) as total,
               SUM(CASE WHEN tool_status = 'error' THEN 1 ELSE 0 END) as errors
        FROM events WHERE source = ? AND ts >= datetime('now', '-24 hours')
        """,
        (source,),
    ).fetchone()
    total_24h = stats_row["total"] or 0
    errors_24h = stats_row["errors"] or 0
    throughput = round(total_24h / 86400, 2)  # events per second

    # Uptime: percentage of 5-min buckets with activity in last 24h
    active_buckets = (
        conn.execute(
            """
        SELECT COUNT(DISTINCT strftime('%Y-%m-%dT%H:', ts) ||
               printf('%02d', (CAST(strftime('%M', ts) AS INT) / 5) * 5)) as cnt
        FROM events WHERE source = ? AND ts >= datetime('now', '-24 hours')
        """,
            (source,),
        ).fetchone()["cnt"]
        or 0
    )
    uptime_pct = round(min(100.0, (active_buckets / 288) * 100), 1)

    # Diagnosis
    is_fresh = (
        conn.execute(
            "SELECT COUNT(*) FROM events WHERE source = ? AND ts >= datetime('now', '-1 hour')",
            (source,),
        ).fetchone()[0]
        > 0
    )
    error_rate = errors_24h / max(total_24h, 1)
    issues: list[str] = []
    if not is_fresh:
        issues.append("No events in last hour")
    if error_rate > 0.1:
        issues.append(f"High error rate: {error_rate:.0%}")
    if uptime_pct < 50:
        issues.append(f"Low uptime: {uptime_pct}%")
    diag_status = "healthy" if not issues else ("degraded" if len(issues) < 2 else "error")

    return {
        "heartbeat": heartbeat,
        "stats": {
            "avg_latency_ms": 0,  # Not tracked yet — placeholder
            "p99_latency_ms": 0,
            "uptime_pct": uptime_pct,
            "errors_24h": errors_24h,
            "throughput_eps": throughput,
        },
        "info": {
            "version": "0.1.0",
            "protocol": "file-watch",
            "adapter": source,
            "pid": os.getpid(),
        },
        "config": {
            "poll_interval_s": 5,
            "batch_size": 100,
            "retry_max": 3,
            "log_path": f"~/.amnesia/logs/{source}.log",
        },
        "diagnosis": {
            "status": diag_status,
            "last_check": row["last_poll_ts"],
            "issues": issues,
        },
    }


# ── Timeline ─────────────────────────────────────────────────────────────────


_TIMELINE_GRANULARITIES = {
    "5min": 5,
    "10min": 10,
    "15min": 15,
    "30min": 30,
    "hour": 60,
    "6hour": 360,
    "day": 1440,
}


@app.get("/api/timeline")
def get_timeline(
    granularity: str = Query(default="hour", pattern="^(5min|10min|15min|30min|hour|6hour|day)$"),
    since: str | None = None,
    until: str | None = None,
):
    conn = _get_conn()

    mins = _TIMELINE_GRANULARITIES[granularity]
    if granularity == "day":
        bucket_expr = "strftime('%Y-%m-%dT00:00:00', ts)"
    elif granularity == "hour":
        bucket_expr = "strftime('%Y-%m-%dT%H:00:00', ts)"
    elif granularity == "6hour":
        bucket_expr = (
            "strftime('%Y-%m-%dT', ts) || "
            "printf('%02d', (CAST(strftime('%H', ts) AS INT) / 6) * 6) || ':00:00'"
        )
    else:
        # Sub-hourly: 5min, 10min, 15min, 30min
        bucket_expr = (
            "strftime('%Y-%m-%dT%H:', ts) || "
            f"printf('%02d', (CAST(strftime('%M', ts) AS INT) / {mins}) * {mins}) || ':00'"
        )

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
