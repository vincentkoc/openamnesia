"""Typed inputs/outputs for Codex source operations."""

from __future__ import annotations

from dataclasses import dataclass

from amnesia.sources.base import BaseInput, BaseOutput


@dataclass(slots=True)
class CodexReadInput(BaseInput):
    pass


@dataclass(slots=True)
class CodexReadOutput(BaseOutput):
    pass
