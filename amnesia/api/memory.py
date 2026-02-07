from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Query

from amnesia.enrichment.vendors import vendor_status
from amnesia.exports.memory import MemoryExportConfig, export_memory

router = APIRouter()


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return datetime.fromisoformat(value).date()


@router.get("/api/memory/daily")
def memory_daily(date_str: str = Query(default=None, alias="date")):
    target = _parse_date(date_str) or datetime.now(UTC).date()
    cfg = MemoryExportConfig(
        enabled=True,
        mode="openclawd",
        output_dir="./exports/memory",
        formats=["json"],
        daily=True,
        weekly=False,
        monthly=False,
        per_project=False,
    )
    paths = export_memory(dsn="sqlite:///./data/amnesia.db", cfg=cfg, target_date=target)
    return {
        "date": target.isoformat(),
        "paths": [str(path) for path in paths],
        "vendors": vendor_status(),
    }


@router.get("/api/memory/daily/latest")
def memory_latest():
    target = datetime.now(UTC).date()
    return memory_daily(date_str=target.isoformat())


@router.get("/api/memory/daily/range")
def memory_range(
    start: str = Query(...),
    end: str = Query(...),
):
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if start_date is None or end_date is None:
        return {"error": "invalid_date"}, 400
    if start_date > end_date:
        return {"error": "start_after_end"}, 400
    cfg = MemoryExportConfig(
        enabled=True,
        mode="openclawd",
        output_dir="./exports/memory",
        formats=["json"],
        daily=True,
        weekly=False,
        monthly=False,
        per_project=False,
    )
    paths = []
    cursor = start_date
    while cursor <= end_date:
        paths.extend(export_memory(dsn="sqlite:///./data/amnesia.db", cfg=cfg, target_date=cursor))
        cursor += timedelta(days=1)
    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "paths": [str(p) for p in paths],
        "vendors": vendor_status(),
    }
