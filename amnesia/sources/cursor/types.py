"""Typed inputs/outputs for Cursor source operations."""

from __future__ import annotations

from dataclasses import dataclass

from amnesia.sources.base import BaseInput, BaseOutput


@dataclass(slots=True)
class CursorReadInput(BaseInput):
    pass


@dataclass(slots=True)
class CursorReadOutput(BaseOutput):
    pass
