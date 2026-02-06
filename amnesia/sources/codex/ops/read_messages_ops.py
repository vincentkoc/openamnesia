"""Placeholder operations for Codex source."""

from __future__ import annotations

from amnesia.models import utc_now
from amnesia.sources.codex.types import CodexReadInput, CodexReadOutput


class ReadOp:
    def run(self, input_data: CodexReadInput) -> CodexReadOutput:
        return CodexReadOutput(source=input_data.source, ts=utc_now(), state=input_data.state)
