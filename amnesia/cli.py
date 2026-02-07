from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class CliDefaults:
    since_days: int = 30
    discovery_limit: int = 500
    mode: str = "recent"
    config_path: str = "config.yaml"


def _load_defaults(config_path: Path) -> CliDefaults:
    if not config_path.exists():
        return CliDefaults(config_path=str(config_path))
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    e2e = raw.get("e2e", {}) or {}
    return CliDefaults(
        since_days=int(e2e.get("since_days", 30)),
        discovery_limit=int(e2e.get("discovery_limit", 500)),
        mode=str(e2e.get("mode", "recent")),
        config_path=str(config_path),
    )


def _prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def _run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def _menu() -> str:
    print("\nOpenAmnesia SDK")
    print("1) Ingest")
    print("2) Discovery")
    print("3) E2E (ingest + discovery)")
    print("4) API server")
    print("5) Frontend dev server")
    print("0) Exit")
    return input("> ").strip()


def _ingest(defaults: CliDefaults) -> int:
    since_days = _prompt("Since days (0 = all)", str(defaults.since_days))
    reset = _prompt("Reset state? (y/n)", "y").lower().startswith("y")
    cmd = ["python", "scripts/run_ingest.py", "--config", defaults.config_path]
    if reset:
        cmd.append("--reset-state")
    if since_days and since_days != "0":
        cmd += ["--since-days", since_days]
    return _run(cmd)


def _discovery(defaults: CliDefaults) -> int:
    source = _prompt("Source (codex/claude/imessage)", "codex")
    limit = _prompt("Limit", str(defaults.discovery_limit))
    since_days = _prompt("Since days (0 = all)", str(defaults.since_days))
    cmd = [
        "python",
        "scripts/run_discovery.py",
        "--source",
        source,
        "--limit",
        limit,
    ]
    if since_days and since_days != "0":
        cmd += ["--since-days", since_days]
    return _run(cmd)


def _e2e(defaults: CliDefaults) -> int:
    mode = _prompt("Mode (recent/all)", defaults.mode)
    cmd = ["python", "scripts/run_e2e.py", "--mode", mode]
    return _run(cmd)


def _api() -> int:
    return _run(["python", "-m", "amnesia.api.server"])


def _frontend() -> int:
    return _run(["npm", "run", "dev", "--prefix", "frontend"])


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAmnesia SDK")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    defaults = _load_defaults(Path(args.config))

    while True:
        choice = _menu()
        if choice == "1":
            _ingest(defaults)
        elif choice == "2":
            _discovery(defaults)
        elif choice == "3":
            _e2e(defaults)
        elif choice == "4":
            _api()
        elif choice == "5":
            _frontend()
        elif choice == "0":
            return 0
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    raise SystemExit(main())
