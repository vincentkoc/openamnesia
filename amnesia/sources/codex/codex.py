"""Public API for Codex source module."""

from __future__ import annotations

from amnesia.sources.codex.ops.read_messages_ops import ReadOp
from amnesia.sources.codex.types import CodexReadInput, CodexReadOutput


def read(input_data: CodexReadInput) -> CodexReadOutput:
    return ReadOp().run(input_data)
