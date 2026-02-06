"""Placeholder operations for Terminal source."""

from __future__ import annotations

from amnesia.models import utc_now
from amnesia.sources.terminal.types import TerminalReadInput, TerminalReadOutput


class ReadOp:
    def run(self, input_data: TerminalReadInput) -> TerminalReadOutput:
        return TerminalReadOutput(source=input_data.source, ts=utc_now(), state=input_data.state)
