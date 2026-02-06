"""Typed inputs/outputs for Terminal source operations."""

from __future__ import annotations

from dataclasses import dataclass

from amnesia.sources.base import BaseInput, BaseOutput


@dataclass(slots=True)
class TerminalReadInput(BaseInput):
    pass


@dataclass(slots=True)
class TerminalReadOutput(BaseOutput):
    pass
