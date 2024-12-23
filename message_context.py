from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Optional

import discord

from command import Command
from exceptions import DiscordMessageMissingException


@dataclass
class MessageContext:
    original_message: Optional[discord.Message] = None
    result: str = ''
    command: Command = field(default_factory=Command.dummy)
    input: object = None
    attachment: discord.File | None = None

    @property
    def message(self) -> discord.Message:
        """
        Wrapper on discord_message to satisfy my desire to have type hints despite possibilirty of original_message being None.
        """
        if self.original_message is None:
            raise DiscordMessageMissingException
        else:
            return self.original_message

    def updated(self, *, result: Optional[str] = None, command: Optional[Command] = None, input: object = None) -> MessageContext:
        if result is None and command is None:
            raise ValueError('Either result or command need to be updated')
        return MessageContext(
            original_message=self.original_message,
            result=result or self.result,
            command=command or self.command,
            input=input,
        )

    @classmethod
    def empty(cls) -> MessageContext:
        return MessageContext()
