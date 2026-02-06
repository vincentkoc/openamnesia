from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class SourceConfig:
    name: str
    enabled: bool = True
    path: str = ""
    pattern: str = "*.log"


@dataclass(slots=True)
class StoreConfig:
    backend: str = "sqlite"
    dsn: str = "sqlite:///./amnesia.db"


@dataclass(slots=True)
class DaemonConfig:
    poll_interval_seconds: int = 5
    state_path: str = ".amnesia_state.yaml"


@dataclass(slots=True)
class ExportConfig:
    enabled: bool = True
    daily_dir: str = "./exports/daily"
    skills_dir: str = "./exports/skills"


@dataclass(slots=True)
class HookConfig:
    plugins: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    sources: list[SourceConfig] = field(default_factory=list)
    store: StoreConfig = field(default_factory=StoreConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    exports: ExportConfig = field(default_factory=ExportConfig)
    hooks: HookConfig = field(default_factory=HookConfig)

    @staticmethod
    def default() -> AppConfig:
        return AppConfig(
            sources=[
                SourceConfig(name="cursor", path="./ingest/cursor", pattern="*.jsonl"),
                SourceConfig(name="codex", path="./ingest/codex", pattern="*.jsonl"),
                SourceConfig(name="terminal", path="./ingest/terminal", pattern="*.log"),
            ]
        )


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return AppConfig.default()

    config_path = Path(path)
    if not config_path.exists():
        return AppConfig.default()

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    source_cfgs = []
    for item in raw.get("sources", []):
        source_cfgs.append(
            SourceConfig(
                name=item["name"],
                enabled=item.get("enabled", True),
                path=item.get("path", ""),
                pattern=item.get("pattern", "*.log"),
            )
        )

    store_raw = raw.get("store", {})
    daemon_raw = raw.get("daemon", {})
    exports_raw = raw.get("exports", {})
    hooks_raw = raw.get("hooks", {})

    return AppConfig(
        sources=source_cfgs or AppConfig.default().sources,
        store=StoreConfig(
            backend=store_raw.get("backend", "sqlite"),
            dsn=store_raw.get("dsn", "sqlite:///./amnesia.db"),
        ),
        daemon=DaemonConfig(
            poll_interval_seconds=int(daemon_raw.get("poll_interval_seconds", 5)),
            state_path=daemon_raw.get("state_path", ".amnesia_state.yaml"),
        ),
        exports=ExportConfig(
            enabled=bool(exports_raw.get("enabled", True)),
            daily_dir=exports_raw.get("daily_dir", "./exports/daily"),
            skills_dir=exports_raw.get("skills_dir", "./exports/skills"),
        ),
        hooks=HookConfig(
            plugins=list(hooks_raw.get("plugins", [])),
        ),
    )


def dump_default_config(path: str | Path) -> None:
    cfg = AppConfig.default()
    payload: dict[str, Any] = {
        "sources": [
            {
                "name": source.name,
                "enabled": source.enabled,
                "path": source.path,
                "pattern": source.pattern,
            }
            for source in cfg.sources
        ],
        "store": {"backend": cfg.store.backend, "dsn": cfg.store.dsn},
        "daemon": {
            "poll_interval_seconds": cfg.daemon.poll_interval_seconds,
            "state_path": cfg.daemon.state_path,
        },
        "exports": {
            "enabled": cfg.exports.enabled,
            "daily_dir": cfg.exports.daily_dir,
            "skills_dir": cfg.exports.skills_dir,
        },
        "hooks": {
            "plugins": cfg.hooks.plugins,
        },
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False)
