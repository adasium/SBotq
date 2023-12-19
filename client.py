import asyncio

import discord

from command import Command
from commands import COMMANDS
from commands import inspire
from commands import markov2
from commands import markov3
from logger import get_logger
from message_context import MessageContext
from settings import DEFAULT_PREFIX
from utils import getenv
from utils import parse_commands


logger = get_logger(__name__)


class Client(discord.Client):
    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        super().__init__()
        self.prefix = prefix
        self.scheduled_commands = [
            inspire,
        ]
        self.markov_blacklisted_channel_ids = [
            int(id)
            for id in getenv('MARKOV_CHANNEL_BLACKLIST').split(';')
        ]

    async def on_ready(self) -> None:
        logger.info('Logged on as %s', self.user)
        for blacklisted_channel_id in self.markov_blacklisted_channel_ids:
            logger.debug('blacklisted channel %s, I cannot eaevesdrop in here', self.get_channel(blacklisted_channel_id))
        await asyncio.create_task(self.scheduler())

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.content.startswith(self.prefix):
            await self.on_message(after)

    async def on_message(self, message: discord.Message) -> None:
        logger.debug('[%s > %s] %s: %s', message.guild.name, message.channel.name, message.author, message.content)
        if message.author == self.user:
            return

        current_context = MessageContext(message=message, result='', command=Command.dummy())

        if not message.content.startswith(self.prefix) and message.channel.id not in self.markov_blacklisted_channel_ids:
            await markov2(current_context, self)
            await markov3(current_context, self)
            return

        command = message.content.removeprefix(self.prefix)
        if len(command) == 0:
            return

        try:
            commands = parse_commands(message.content, prefix=self.prefix)
            logger.debug('parsed commands %s', commands)
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

    async def scheduler(self) -> None:
        while True:
            for command in self.scheduled_commands:
                await asyncio.create_task(command(message=None, client=self))
            await asyncio.sleep(24 * 60 * 60)
