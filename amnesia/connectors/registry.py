from __future__ import annotations

from importlib import import_module
from pathlib import Path

from amnesia.config import SourceConfig
from amnesia.connectors.base import ConnectorSettings, SourceConnector
from amnesia.connectors.claude import ClaudeConnector
from amnesia.connectors.codex import CodexConnector
from amnesia.connectors.cursor import CursorConnector
from amnesia.connectors.file_drop import FileDropConnector
from amnesia.connectors.imessage import IMessageConnector
from amnesia.connectors.terminal import TerminalConnector
from amnesia.sources.registry import validate_source_module_structure


def _connector_from_source_name(source_name: str):
    builtins: dict[str, type] = {
        "claude": ClaudeConnector,
        "cursor": CursorConnector,
        "codex": CodexConnector,
        "terminal": TerminalConnector,
        "imessage": IMessageConnector,
    }
    if source_name in builtins:
        return builtins[source_name]

    module_name = f"amnesia.connectors.{source_name}"
    class_name = "".join(part.capitalize() for part in source_name.split("_")) + "Connector"
    try:
        module = import_module(module_name)
    except ImportError:
        return FileDropConnector
    return getattr(module, class_name, FileDropConnector)


def build_connectors(sources: list[SourceConfig]) -> list[SourceConnector]:
    connectors: list[SourceConnector] = []

    for source in sources:
        if not source.enabled:
            continue

        validate_source_module_structure(source.name)

        settings = ConnectorSettings(
            source_name=source.name,
            root_path=Path(source.path).expanduser(),
            pattern=source.pattern,
            options=source.options,
        )

        connector_cls = _connector_from_source_name(source.name)
        connectors.append(connector_cls(settings=settings))

    return connectors
