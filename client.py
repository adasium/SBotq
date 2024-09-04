import asyncio

import discord
import pendulum

import monkeypatch
import settings
from command import Command
from commands import carrot
from commands import generate_markov2
from commands import generate_markov_at_random_time
from commands import get_builtin_command
from commands import markov2
from commands import markov3
from commands import next_bernardynki
from commands import parse_pipe
from exceptions import CommandNotFound
from getenv import getenv
from logger import get_logger
from message_context import MessageContext
from utils import next_call_timestamp
from utils import remove_prefix


logger = get_logger(__name__)


discord.gateway.KeepAliveHandler.run = monkeypatch.run


class MsgCtx:
    def __init__(self, client: discord.Client, message: discord.Message) -> None:
        self.client = client
        self.message = message

    @property
    def is_mentioned_directly(self) -> bool:
        return self.client.user.mentioned_in(self.message)

    @property
    def is_mentioned_via_role(self) -> bool:
        return set(self.message.guild.me.roles).intersection(set(self.message.role_mentions))

    @property
    def is_mentioned(self) -> bool:
        return self.is_mentioned_directly or self.is_mentioned_via_role

    @property
    def is_command(self) -> bool:
        return self.message.content.startswith(self.client.prefix)

    @property
    def is_beta_command(self) -> bool:
        return self.message.content.startswith(settings.BETA_PREFIX)

    @property
    def _is_commandlike(self) -> bool:
        return self.message.content.startswith(settings.COMMON_PREFIXES)

    @property
    def should_markovify(self) -> bool:
        return (
            not self._is_commandlike
            and self.message.channel.id not in self.client.markov_blacklisted_channel_ids
        )


class Client(discord.Client):
    def __init__(self, prefix: str = settings.PREFIX) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.prefix = prefix
        self.scheduled_commands = [
            #daily_inspiration,
            next_bernardynki,
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
        if after.content.startswith(settings.COMMON_PREFIXES):
            await self.on_message(after)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        message = await self.get_channel(payload.channel_id).fetch_message(payload.message_id)
        message_reaction = [
            r for r in message.reactions
            if (payload.emoji.is_custom_emoji() and payload.emoji == r.emoji)
            or (not payload.emoji.is_custom_emoji() and payload.emoji.name == r.emoji)
        ][0]
        if message_reaction.me:
            return None
        logger.debug('somebody reacted: %s reaction_count: %s', payload.emoji, message_reaction.count)
        if message_reaction.count >= 3:
            await message.add_reaction(payload.emoji)

    async def on_message(self, message: discord.Message) -> None:
        logger.debug('[%s > %s] %s: %s', message.guild.name, message.channel.name, message.author, message.content)

        if self._is_self_message(message):
            return None

        _message_context = self._build_message_context(message)

        if _message_context.is_mentioned:
            logger.debug('-> [client.on_message.mention]')
            current_context = MessageContext(discord_message=message, result='', command=Command.dummy())
            generated_markov = (await generate_markov2(current_context, self)).result
            await message.channel.send(generated_markov)
            return None

        if _message_context.should_markovify:
            logger.debug('-> [client.on_message.markovifying]')
            current_context = MessageContext(discord_message=message, result='', command=Command.dummy())
            await markov2(current_context, self)
            await markov3(current_context, self)
            await carrot(current_context, self)
            return None

        if not _message_context.is_command:
            return None

        if len(remove_prefix(text=message.content, prefix=self.prefix)) == 0:
            return None

        try:
            logger.debug('-> [client.on_message.command]')
            pipe = parse_pipe(message.content, prefix=self.prefix)
            current_context = MessageContext(message)
        except CommandNotFound as e:
            return await message.channel.send(f'Command `{e.value}` not found')

        try:
            for command in pipe:
                cmd_func = get_builtin_command(command.name)
                current_context.command = command
                current_context = await cmd_func(current_context, self)
            if len(current_context.result.strip()) > 0:
                return await message.channel.send(current_context.result)
        except Exception as e:
            return await message.channel.send(str(e))

    async def scheduler(self) -> None:
        now = pendulum.now(pendulum.UTC)
        when_should_be_called = {
            command: next_call_timestamp(now, command.scheduled_at, command.scheduled_every)
            for command in self.scheduled_commands
        }
        while True:
            try:
                now = pendulum.now(pendulum.UTC)
                for command in self.scheduled_commands:
                    is_the_high_time = when_should_be_called[command] < now
                    is_condition_fulfilled = command.condition is None or command.condition(now)
                    # lambda dt: (Bernardynki.next_after(dt).when - dt).in_days()
                    if is_the_high_time and is_condition_fulfilled:
                        await asyncio.create_task(command(context=None, client=self))
                        when_should_be_called[command] = when_should_be_called[command] + command.scheduled_every
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.exception(e)

    def _is_self_message(self, message: discord.Message) -> bool:
        return message.author == self.user

    def _build_message_context(self, message: discord.Message) -> MsgCtx:
        return MsgCtx(
            client=self,
            message=message,
        )
