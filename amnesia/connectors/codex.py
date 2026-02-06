from __future__ import annotations

from dataclasses import dataclass

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.file_drop import FileDropConnector


@dataclass(slots=True)
class CodexConnector(FileDropConnector):
    settings: ConnectorSettings
