import asyncio
from datetime import datetime
from datetime import time
from datetime import timedelta

import discord
from sqlalchemy import select

from command import Command
from command import parse_commands
from commands import carrot
from commands import COMMANDS
from commands import daily_inspiration
from commands import generate_markov2
from commands import generate_markov_at_random_time
from commands import markov2
from commands import markov3
from commands import SPECIAL_COMMANDS
from database import get_db
from getenv import getenv
from logger import get_logger
from message_context import MessageContext
from models import CommandModel
from models import VariableModel
from settings import DEFAULT_PREFIX
from utils import is_special_command
from utils import remove_prefix


logger = get_logger(__name__)


class Client(discord.Client):
    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.prefix = prefix
        self.scheduled_commands = [
            daily_inspiration,
        ]
        self.markov_blacklisted_channel_ids = [
            int(id)
            for id in getenv('MARKOV_CHANNEL_BLACKLIST').split(';')
        ]

    async def on_ready(self) -> None:
        logger.info('Logged on as %s', self.user)
        for blacklisted_channel_id in self.markov_blacklisted_channel_ids:
            logger.debug(
                'blacklisted channel %s, I cannot eaevesdrop in here',
                self.get_channel(blacklisted_channel_id),
            )

        await asyncio.gather(
            *[
                self.scheduler(),
                generate_markov_at_random_time(context=MessageContext.empty(), client=self),
            ], return_exceptions=True,
        )

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.content.startswith(self.prefix):
            await self.on_message(after)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        message = await self.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction_count = len([r for r in message.reactions if r.emoji == payload.emoji])
        logger.debug('somebody reacted: %s reaction_count: %s', payload.emoji, reaction_count)
        if reaction_count >= 3:
            await message.add_reaction(payload.emoji)

    async def on_message(self, message: discord.Message) -> None:
        logger.debug('[%s > %s] %s: %s', message.guild.name, message.channel.name, message.author, message.content)
        if message.author == self.user:
            return

        current_context = MessageContext(discord_message=message, result='', command=Command.dummy())

        is_mentioned_directly = self.user.mentioned_in(message)
        is_mentioned_via_role = set(message.guild.me.roles).intersection(set(message.role_mentions))
        if is_mentioned_directly or is_mentioned_via_role:
            if message.content == '<@!%s>' % self.user.id:
                mention_msg = 'sup'
                with get_db() as db:
                    fetched_mention_msg = db.execute(
                        select(VariableModel)
                        .where(VariableModel.name == 'MENTION_GREETING'),
                    ).scalar_one_or_none()
                    if fetched_mention_msg is not None:
                        mention_msg = fetched_mention_msg.value
                await message.channel.send(f'{message.author.mention} {mention_msg}')
            else:
                generated_markov = (await generate_markov2(current_context, self)).result
                await message.channel.send(generated_markov)
            return

        if not message.content.startswith(self.prefix) and message.channel.id not in self.markov_blacklisted_channel_ids:
            await markov2(current_context, self)
            await markov3(current_context, self)
            await carrot(current_context, self)
            return

        if len(remove_prefix(text=message.content, prefix=self.prefix)) == 0:
            return

        if is_special_command(message.content, commands=COMMANDS, special_commands=SPECIAL_COMMANDS):
            command = Command.from_str(message.content)
            special_command_context = await COMMANDS[command.name](current_context.updated(command=command), self)
            return await message.channel.send(special_command_context.result)

        try:
            commands = parse_commands(message.content, prefix=self.prefix)
            logger.debug('parsed commands %s', commands)
            for command in commands:
                if command.name not in COMMANDS:
                    with get_db() as db:
                        fetched_command = db.execute(
                            select(CommandModel)
                            .where(CommandModel.name == command.name),
                        ).scalar_one_or_none()
                        if fetched_command is not None:
                            logger.debug('Fetched command: [%s|%s]', fetched_command.name, fetched_command.command)
                            for c in parse_commands(fetched_command.command):
                                logger.debug('Executing fetched command: [%s|%s]', c.name, c.raw_args)
                                current_context = await COMMANDS[c.name](current_context.updated(command=c), self)
                            continue
                    return await message.channel.send(f'Command {command.name} not found')
                logger.debug('Executing normal command: %s', command.name)
                command_func = COMMANDS[command.name]
                current_context = await command_func(current_context.updated(command=command), self)

            logger.debug('Final result of %s: %s', message.content, current_context.result)
            if current_context.result:
                await message.channel.send(current_context.result)
        except ValueError as e:
            logger.exception(e)

    async def scheduler(self) -> None:
        now = datetime.now()
        when_should_be_called = {
            command: next_call_timestamp(now, command.scheduled_at, command.scheduled_every)
            for command in self.scheduled_commands
        }
        while True:
            for command in self.scheduled_commands:
                if when_should_be_called[command] < datetime.now():
                    await asyncio.create_task(command(context=None, client=self))
                    when_should_be_called[command] = next_call_timestamp(datetime.now(), command.scheduled_at, command.scheduled_every)
            await asyncio.sleep(1)


def next_call_timestamp(now: datetime, scheduled_at: time, scheduled_every: timedelta) -> datetime:
    candidate = datetime(now.year, now.month, now.day, scheduled_at.hour, scheduled_at.minute)
    while candidate < now:
        candidate += scheduled_every
    return candidate
