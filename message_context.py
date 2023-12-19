from __future__ import annotations

from typing import NamedTuple

import discord


class MessageContext(NamedTuple):
    message: discord.Message
    result: str

    def updated(self, result: str) -> MessageContext:
        return MessageContext(
            message=self.message,
            result=result,
        )
