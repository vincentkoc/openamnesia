from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from amnesia.pipeline.base import PipelineContext

HookFn = Callable[[PipelineContext], PipelineContext]


@dataclass(slots=True)
class HookRegistry:
    pre_normalize: list[HookFn] = field(default_factory=list)
    post_normalize: list[HookFn] = field(default_factory=list)
    post_sessionize: list[HookFn] = field(default_factory=list)
    post_momentize: list[HookFn] = field(default_factory=list)
    post_extract: list[HookFn] = field(default_factory=list)
    post_skill_mine: list[HookFn] = field(default_factory=list)

    def run(self, hooks: list[HookFn], ctx: PipelineContext) -> PipelineContext:
        for hook in hooks:
            ctx = hook(ctx)
        return ctx
