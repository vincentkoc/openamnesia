from __future__ import annotations

from datetime import timezone
from pathlib import Path

from amnesia.models import Moment


def export_daily_moments(moments: list[Moment], out_dir: str = "./exports/daily") -> list[Path]:
    by_day: dict[str, list[Moment]] = {}

    for moment in moments:
        iso_ts = moment.evidence_json.get("day_ts")
        if isinstance(iso_ts, str) and iso_ts:
            day_key = iso_ts[:10].replace("-", "_")
        else:
            day_key = "unknown_day"
        by_day.setdefault(day_key, []).append(moment)

    out_paths: list[Path] = []
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    for day_key, day_moments in by_day.items():
        out_path = root / f"{day_key}.md"
        lines = [f"# Amnesia Daily {day_key}", ""]
        for moment in day_moments:
            lines.append(f"## {moment.intent} [{moment.outcome}]")
            lines.append(moment.summary)
            lines.append("")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        out_paths.append(out_path)

    return out_paths
