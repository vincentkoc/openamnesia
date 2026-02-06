"""Public API for iMessage source module."""

from __future__ import annotations

from amnesia.sources.imessage.ops.read_messages_ops import ReadMessagesOp
from amnesia.sources.imessage.types import IMessageReadInput, IMessageReadOutput


def read_messages(input_data: IMessageReadInput) -> IMessageReadOutput:
    return ReadMessagesOp().run(input_data)
