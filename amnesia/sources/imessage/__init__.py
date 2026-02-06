"""iMessage source module package."""

from amnesia.sources.imessage.imessage import read_messages
from amnesia.sources.imessage.types import IMessageMessage, IMessageReadInput, IMessageReadOutput

__all__ = ["IMessageMessage", "IMessageReadInput", "IMessageReadOutput", "read_messages"]
