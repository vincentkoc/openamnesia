"""Placeholder operations for Cursor source."""

from __future__ import annotations

from amnesia.models import utc_now
from amnesia.sources.cursor.types import CursorReadInput, CursorReadOutput


class ReadOp:
    def run(self, input_data: CursorReadInput) -> CursorReadOutput:
        return CursorReadOutput(source=input_data.source, ts=utc_now(), state=input_data.state)
