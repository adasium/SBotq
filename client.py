import discord

from commands import COMMANDS
from logger import logger
from message_context import MessageContext


class Client(discord.Client):
    def __init__(self, prefix: str = '!') -> None:
        super().__init__()
        self.prefix = prefix

    async def on_ready(self) -> None:
        logger.info('Logged on as %s', self.user)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.content.startswith(self.prefix):
            await self.on_message(after)

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        if not message.content.startswith(self.prefix):
            return

        command = message.content.removeprefix(self.prefix)
        if len(command) == 0:
            return

        command_func = COMMANDS.get(command.split()[0])
        if command_func is not None:
            context: MessageContext = await command_func(MessageContext(message=message, result=command), self)
            await message.channel.send(context.result)
