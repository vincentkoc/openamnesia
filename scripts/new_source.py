#!/usr/bin/env python3
"""Scaffold a new source package and optional connector."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new OpenAmnesia source scaffold")
    parser.add_argument("name", help="Source name in snake_case (e.g. slack_export)")
    parser.add_argument(
        "--with-connector",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate amnesia/connectors/<name>.py",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    return parser.parse_args()


def _camel(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _write(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _validate_name(name: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise SystemExit("Source name must be snake_case (letters, numbers, underscores).")


def main() -> int:
    args = _parse_args()
    source_name = args.name.strip()
    _validate_name(source_name)
    source_class = _camel(source_name)

    root = Path(__file__).resolve().parent.parent
    base = root / "amnesia" / "sources" / source_name

    _write(
        base / "__init__.py",
        f'"""Source module for {source_name}."""\n',
        force=args.force,
    )
    _write(
        base / "helpers.py",
        f'"""Helpers for {source_name} source."""\n',
        force=args.force,
    )
    _write(
        base / "reporting.py",
        f'"""Reporting helpers for {source_name} source."""\n',
        force=args.force,
    )
    _write(
        base / "types.py",
        f'''"""Typed inputs/outputs for {source_name} source operations."""

from __future__ import annotations

from dataclasses import dataclass

from amnesia.sources.base import BaseInput, BaseOutput


@dataclass(slots=True)
class {source_class}ReadInput(BaseInput):
    pass


@dataclass(slots=True)
class {source_class}ReadOutput(BaseOutput):
    pass
''',
        force=args.force,
    )
    _write(
        base / f"{source_name}.py",
        f'''"""Public API for {source_name} source module."""

from __future__ import annotations

from amnesia.sources.{source_name}.ops.read_messages_ops import ReadMessagesOp
from amnesia.sources.{source_name}.types import {source_class}ReadInput, {source_class}ReadOutput


def read(input_data: {source_class}ReadInput) -> {source_class}ReadOutput:
    return ReadMessagesOp().run(input_data)
''',
        force=args.force,
    )
    _write(
        base / "ops" / "__init__.py",
        "from __future__ import annotations\n\n"
        "from amnesia.sources."
        f"{source_name}.ops.read_messages_ops import ReadMessagesOp\n\n"
        '__all__ = ["ReadMessagesOp"]\n',
        force=args.force,
    )
    _write(
        base / "ops" / "read_messages_ops.py",
        f'''"""Read operations for {source_name} source."""

from __future__ import annotations

from amnesia.models import utc_now
from amnesia.sources.{source_name}.types import {source_class}ReadInput, {source_class}ReadOutput


class ReadMessagesOp:
    def run(self, input_data: {source_class}ReadInput) -> {source_class}ReadOutput:
        return {source_class}ReadOutput(
            source=input_data.source,
            ts=utc_now(),
            state=input_data.state,
            meta={{"source": "{source_name}"}},
        )
''',
        force=args.force,
    )

    if args.with_connector:
        connector_path = root / "amnesia" / "connectors" / f"{source_name}.py"
        _write(
            connector_path,
            f"""from __future__ import annotations

from dataclasses import dataclass

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.file_drop import FileDropConnector


@dataclass(slots=True)
class {source_class}Connector(FileDropConnector):
    settings: ConnectorSettings
""",
            force=args.force,
        )

    print(f"Scaffolded source: {source_name}")
    print(f"- package: {base}")
    if args.with_connector:
        print(f"- connector: {root / 'amnesia' / 'connectors' / f'{source_name}.py'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
