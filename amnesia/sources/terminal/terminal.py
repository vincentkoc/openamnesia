"""Public API for Terminal source module."""

from __future__ import annotations

from amnesia.sources.terminal.ops.read_messages_ops import ReadOp
from amnesia.sources.terminal.types import TerminalReadInput, TerminalReadOutput


def read(input_data: TerminalReadInput) -> TerminalReadOutput:
    return ReadOp().run(input_data)
