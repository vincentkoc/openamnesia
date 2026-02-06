"""Public API for Cursor source module."""

from __future__ import annotations

from amnesia.sources.cursor.ops.read_messages_ops import ReadOp
from amnesia.sources.cursor.types import CursorReadInput, CursorReadOutput


def read(input_data: CursorReadInput) -> CursorReadOutput:
    return ReadOp().run(input_data)
