from __future__ import annotations

from typing import NamedTuple

import discord

from command import Command


class MessageContext(NamedTuple):
    message: discord.Message
    result: str
    command: Command

    def updated(self, *, result: str | None = None, command: Command | None = None) -> MessageContext:
        if result is None and command is None:
            raise ValueError('Either result or command need to be updated')
        return MessageContext(
            message=self.message,
            result=result or self.result,
            command=command or self.command,
        )
