from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Optional

import discord

from command import Command
from exceptions import DiscordMessageMissingException


@dataclass
class MessageContext:
    discord_message: Optional[discord.Message] = None
    result: str = ''
    command: Command = field(default_factory=Command.dummy)

    @property
    def message(self) -> discord.Message:
        """
        Wrapper on discord_message to satisfy my desire to have type hints despite possibilirty of discord_message being None.
        """
        if self.discord_message is None:
            raise DiscordMessageMissingException
        else:
            return self.discord_message

    def updated(self, *, result: Optional[str] = None, command: Optional[Command] = None) -> MessageContext:
        if result is None and command is None:
            raise ValueError('Either result or command need to be updated')
        return MessageContext(
            discord_message=self.discord_message,
            result=result or self.result,
            command=command or self.command,
        )

    @classmethod
    def empty(cls) -> MessageContext:
        return MessageContext()
