from __future__ import annotations

import argparse
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

from amnesia.config import AppConfig, dump_default_config, load_config
from amnesia.connectors.registry import build_connectors
from amnesia.exports.md_daily import export_daily_moments
from amnesia.exports.skill_yaml import export_skills_yaml
from amnesia.models import IngestAudit, SourceStatus, utc_now
from amnesia.pipeline.base import PipelineContext
from amnesia.pipeline.extract import annotate_moments
from amnesia.pipeline.hooks import HookRegistry
from amnesia.pipeline.momentize import momentize_sessions
from amnesia.pipeline.normalize import normalize_records
from amnesia.pipeline.optimize import optimize_skill
from amnesia.pipeline.plugin_loader import load_plugins
from amnesia.pipeline.sessionize import sessionize_events
from amnesia.pipeline.skill_mine import mine_skill_candidates
from amnesia.store.factory import build_store


@dataclass(slots=True)
class RuntimeState:
    per_source: dict

    @staticmethod
    def empty() -> RuntimeState:
        return RuntimeState(per_source={})


def load_state(path: Path) -> RuntimeState:
    if not path.exists():
        return RuntimeState.empty()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return RuntimeState(per_source=raw.get("per_source", {}))


def save_state(path: Path, state: RuntimeState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"per_source": state.per_source}
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=True)


class Daemon:
    def __init__(self, config: AppConfig):
        self.config = config
        self.connectors = build_connectors(config.sources)
        self.store = build_store(config.store)
        self.state_path = Path(config.daemon.state_path)
        self.state = load_state(self.state_path)
        self.hooks = HookRegistry()
        load_plugins(config.hooks.plugins, self.hooks)
        self.running = True

    def stop(self, *_args: object) -> None:
        self.running = False

    def run(self, once: bool = False) -> None:
        self.store.init_schema()

        while self.running:
            total_records = 0

            for connector in self.connectors:
                source_name = connector.source_name
                source_state = self.state.per_source.get(source_name, {})
                now = utc_now()

                try:
                    records, new_source_state = connector.poll(source_state)
                    self.state.per_source[source_name] = new_source_state
                    total_records += len(records)

                    if records:
                        self._process_records(source_name, records)

                    self.store.save_source_status(
                        SourceStatus(
                            source=source_name,
                            status="ingesting" if records else "idle",
                            last_poll_ts=now,
                            records_seen=len(records),
                            records_ingested=len(records),
                            error_message=None,
                        )
                    )
                except Exception as exc:
                    self.store.save_source_status(
                        SourceStatus(
                            source=source_name,
                            status="error",
                            last_poll_ts=now,
                            records_seen=0,
                            records_ingested=0,
                            error_message=str(exc),
                        )
                    )

            save_state(self.state_path, self.state)

            if once:
                break

            if total_records == 0:
                time.sleep(self.config.daemon.poll_interval_seconds)

        self.store.close()

    def print_source_status(self) -> None:
        self.store.init_schema()
        statuses = self.store.list_source_status()
        configured = [src.name for src in self.config.sources if src.enabled]
        known = {status.source for status in statuses}

        for status in statuses:
            print(
                f"{status.source:10} status={status.status:9} ingested={status.records_ingested:4}"
                f" last={status.last_poll_ts.isoformat()}"
            )

        for source in configured:
            if source not in known:
                print(f"{source:10} status=never-run")

        self.store.close()

    def _process_records(self, source_name: str, records: list) -> None:
        ctx = PipelineContext()
        ctx.derived["records"] = records

        ctx = self.hooks.run(self.hooks.pre_normalize, ctx)
        ctx.events = normalize_records(records)
        ctx = self.hooks.run(self.hooks.post_normalize, ctx)

        ctx.sessions = sessionize_events(ctx.events)
        ctx = self.hooks.run(self.hooks.post_sessionize, ctx)

        ctx.moments = momentize_sessions(ctx.sessions)
        ctx = self.hooks.run(self.hooks.post_momentize, ctx)

        ctx.moments = annotate_moments(ctx.moments, ctx.events)
        ctx = self.hooks.run(self.hooks.post_extract, ctx)

        candidates = mine_skill_candidates(ctx.moments)
        optimized = [optimize_skill(skill) for skill in candidates]
        ctx.derived["skills"] = optimized
        ctx = self.hooks.run(self.hooks.post_skill_mine, ctx)

        inserted_events = self.store.save_events(ctx.events)
        inserted_sessions = self.store.save_sessions(ctx.sessions)
        inserted_moments = self.store.save_moments(ctx.moments)
        inserted_skills = self.store.save_skill_candidates(ctx.derived["skills"])

        if self.config.exports.enabled:
            export_daily_moments(ctx.moments, out_dir=self.config.exports.daily_dir)
            export_skills_yaml(ctx.derived["skills"], out_dir=self.config.exports.skills_dir)

        self.store.append_ingest_audit(
            IngestAudit(
                audit_id=str(uuid.uuid4()),
                ts=utc_now(),
                source=source_name,
                event_count=inserted_events,
                session_count=inserted_sessions,
                moment_count=inserted_moments,
                skill_count=inserted_skills,
                details_json={"records": len(records)},
            )
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Amnesia local ingestion daemon")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config")
    parser.add_argument("--init-config", action="store_true", help="Write default config and exit")
    parser.add_argument("--once", action="store_true", help="Run one ingestion pass and exit")
    parser.add_argument("--sources", action="store_true", help="Print source statuses and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.init_config:
        dump_default_config(args.config)
        print(f"Wrote default config to {args.config}")
        return 0

    config = load_config(args.config)
    daemon = Daemon(config)

    if args.sources:
        daemon.print_source_status()
        return 0

    signal.signal(signal.SIGINT, daemon.stop)
    signal.signal(signal.SIGTERM, daemon.stop)

    daemon.run(once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
