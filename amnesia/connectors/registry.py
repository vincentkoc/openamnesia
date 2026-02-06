from __future__ import annotations

from pathlib import Path

from amnesia.config import SourceConfig
from amnesia.connectors.base import ConnectorSettings, SourceConnector
from amnesia.connectors.codex import CodexConnector
from amnesia.connectors.cursor import CursorConnector
from amnesia.connectors.imessage import IMessageConnector
from amnesia.connectors.terminal import TerminalConnector
from amnesia.sources.registry import validate_source_module_structure


def build_connectors(sources: list[SourceConfig]) -> list[SourceConnector]:
    connectors: list[SourceConnector] = []

    for source in sources:
        if not source.enabled:
            continue

        validate_source_module_structure(source.name)

        settings = ConnectorSettings(
            source_name=source.name,
            root_path=Path(source.path),
            pattern=source.pattern,
            options=source.options,
        )

        match source.name:
            case "cursor":
                connectors.append(CursorConnector(settings=settings))
            case "codex":
                connectors.append(CodexConnector(settings=settings))
            case "terminal":
                connectors.append(TerminalConnector(settings=settings))
            case "imessage":
                connectors.append(IMessageConnector(settings=settings))
            case _:
                connectors.append(TerminalConnector(settings=settings))

    return connectors
