import discord

from command import Command
from commands import COMMANDS
from logger import logger
from message_context import MessageContext
from settings import DEFAULT_PREFIX
from utils import parse_commands


class Client(discord.Client):
    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
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

        try:
            commands = parse_commands(message.content, prefix=self.prefix)
            logger.debug('parsed commands %s', commands)
            current_context = MessageContext(message=message, result='', command=Command.dummy())
            for command in commands:
                if command.name not in COMMANDS:
                    await message.channel.send(f'Command {command.name} not found')
                else:
                    command_func = COMMANDS[command.name]
                    current_context = await command_func(current_context.updated(command=command), self)
            if current_context.result:
                await message.channel.send(current_context.result)
        except ValueError as e:
            logger.exception(e)
