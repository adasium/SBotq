from __future__ import annotations
import discord
from typing import NamedTuple


class MessageContext(NamedTuple):
    message: discord.Message
    result: str

    def updated(self, result: str) -> MessageContext:
        return MessageContext(
            message=self.message,
            result=result,
        )
