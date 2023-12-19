from __future__ import annotations

import io
import random
from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import TYPE_CHECKING

import discord
import requests
from PIL import Image
from sqlalchemy import and_
from sqlalchemy import delete
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update

from database import get_db
from decorators import daily
from logger import get_logger
from message_context import MessageContext
from models import CommandModel
from models import Markov2
from models import Markov3
from models import VariableModel
from settings import DISCORD_MESSAGE_LIMIT
from settings import MARKOV_MIN_WORD_COUNT
from utils import Buf
from utils import get_markov_weights
from utils import getenv
from utils import shuffle_str
from utils import window

if TYPE_CHECKING:
    from client import Client
    CommandFunc = Callable[[MessageContext, Client], Awaitable[MessageContext]]


logger = get_logger(__name__)

COMMANDS = {}
HIDDEN_COMMANDS = {}
SPECIAL_COMMANDS = {}


def command(*, name: str, hidden: bool = False, special: bool = False) -> Callable[[CommandFunc], CommandFunc]:
    def decorator(func: CommandFunc) -> CommandFunc:
        @wraps(func)
        async def wrapper(context: MessageContext, client: Client) -> MessageContext:
            return await func(context, client)
        if not hidden:
            COMMANDS[name] = wrapper
        else:
            HIDDEN_COMMANDS[name] = wrapper
        if special:
            SPECIAL_COMMANDS[name] = wrapper
        return wrapper
    return decorator


@command(name='ping')
async def ping(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(result='pong')


@command(name='bing')
async def bing(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(result='bong')


@command(name='commands')
async def commands(context: MessageContext, client: Client) -> MessageContext:
    prefix = client.prefix
    result = ', '.join(f'{prefix}{command}' for command in sorted(COMMANDS))
    return context.updated(result=result)


@command(name='random')
async def random_(context: MessageContext, client: Client) -> MessageContext:
    try:
        logger.debug('%s', context.result)
        cmd = context.command
        if len(cmd.args) == 0:
            return context.updated(result=str(random.random()))
        elif len(cmd.args) == 1:
            return context.updated(result=str(random.randint(0, int(cmd.args[0]))))
        elif len(cmd.args) == 2:
            return context.updated(result=str(random.randint(int(cmd.args[0]), int(cmd.args[1]))))
        return context.updated(result='Co za dużo to niezdrowo')
    except ValueError as e:
        logger.exception(e)
        return context.updated(result=str(e))
    return context.updated(result='Coś ty narobił')


@command(name='echo')
async def echo(context: MessageContext, client: Client) -> MessageContext:
    if context.command.raw_args:
        content = context.command.raw_args
    else:
        content = ' '.join([context.result] * 2)
    return context.updated(result=content)


@command(name='scream')
async def scream(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(result=context.result.upper())


@command(name='shrug')
async def shrug(context: MessageContext, client: Client) -> MessageContext:
    if context.command.raw_args:
        content = context.command.raw_args
    else:
        content = context.result
    result = rf'¯\\\_{content}_/¯'
    return context.updated(result=result)


@command(name='shuffle_words')
async def shuffle_words(context: MessageContext, client: Client) -> MessageContext:
    if context.command.raw_args:
        content = context.command.raw_args
    else:
        content = context.result
    return context.updated(result=' '.join(shuffle_str(word) for word in content.split()))


@command(name='chid')
async def chid(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(result=str(context.message.channel.id))


@command(name='myid')
async def myid(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(result=str(context.message.author.id))


@command(name='markov2', hidden=True)
async def markov2(context: MessageContext, client: Client) -> MessageContext:
    parts = context.message.content.split()
    if len(parts) < 2:
        return context

    with get_db() as db:
        for word1, word2 in window([None] + parts + [None], n=2):
            result = db.execute(
                update(Markov2)
                .where(
                    and_(
                        Markov2.word1 == word1,
                        Markov2.word2 == word2,
                        Markov2.channel_id == context.message.channel.id,
                        Markov2.guild_id == context.message.guild.id,
                    ),
                )
                .values(counter=Markov2.counter + 1),
            )
            if result.rowcount == 0:  # type: ignore
                db.add(
                    Markov2(
                        word1=word1,
                        word2=word2,
                        channel_id=context.message.channel.id,
                        guild_id=context.message.guild.id,
                    ),
                )
        db.commit()
    return context


@command(name='markov3', hidden=True)
async def markov3(context: MessageContext, client: Client) -> MessageContext:
    parts = context.message.content.split()
    if len(parts) < 3:
        return context

    with get_db() as db:
        for word1, word2, word3 in window([None] + parts + [None], n=3):
            result = db.execute(
                update(Markov3)
                .where(
                    and_(
                        Markov3.word1 == word1,
                        Markov3.word2 == word2,
                        Markov3.word3 == word3,
                        Markov3.channel_id == context.message.channel.id,
                        Markov3.guild_id == context.message.guild.id,
                    ),
                )
                .values(counter=Markov3.counter + 1),
            )
            if result.rowcount == 0:  # type: ignore
                db.add(
                    Markov3(
                        word1=word1,
                        word2=word2,
                        word3=word3,
                        channel_id=context.message.channel.id,
                        guild_id=context.message.guild.id,
                    ),
                )
        db.commit()
    return context


@command(name='inspire', hidden=False)
async def inspire(context: MessageContext, client: Client) -> MessageContext:
    logger.info('Sending an inspiring message.')
    response = requests.get('https://inspirobot.me/api?generate=true')
    image = Image.open(requests.get(response.text, stream=True).raw)
    with io.BytesIO() as image_binary:
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        channel = client.get_channel(getenv('INSPIRATIONAL_MESSAGE_CHANNEL_ID', as_=int))
        await channel.send(
            file=discord.File(fp=image_binary, filename='daily_inspiration.png'),
        )
    return context


@daily(at='8:00')
@command(name='daily_inspiration', hidden=True)
async def daily_inspiration(context: MessageContext, client: Client) -> MessageContext:
    channel = client.get_channel(getenv('INSPIRATIONAL_MESSAGE_CHANNEL_ID', as_=int))
    await channel.send('Miłego dnia i smacznej kawusi <3')
    await inspire(context=context, client=client)  # type: ignore
    return context


@command(name='train_markov', hidden=True)
async def train_markov(context: MessageContext, client: Client) -> MessageContext:
    i = 1
    async for message in context.message.channel.history(limit=None):
        i += 1
        logger.debug('Training on channel %s: message no %s', message.channel, i)
        if (
                message.author != client.user
                and not message.content.startswith(client.prefix)
                and len(message.content.split()) > MARKOV_MIN_WORD_COUNT
        ):
            await markov2(MessageContext(message=message), client)
            await markov3(MessageContext(message=message), client)
    logger.debug('DONE TRAINING ON CHANNEL %s', context.message.channel)
    return context


@command(name='m', hidden=False)
async def generate_markov2(context: MessageContext, client: Client) -> MessageContext:
    try:
        markov_message = context.command.args
        previous_message: Optional[str] = context.command.args[-1]
    except IndexError:
        markov_message = []
        previous_message = None

    with get_db() as db:
        while True:
            candidates = db.execute(
                select(Markov2)
                .where(
                    Markov2.word1 == previous_message,
                ),
            ).scalars().all()

            if len(candidates) == 0:
                return context.updated(result=context.result + ' ' + ' '.join(markov_message))

            [candidate] = random.choices(candidates, get_markov_weights(candidates))
            if candidate is None:
                return context.updated(result=context.result + ' ' + ' '.join(markov_message))

            previous_message = candidate.word2
            if previous_message is None or len(' '.join(markov_message + [previous_message])) > DISCORD_MESSAGE_LIMIT:
                return context.updated(result=context.result + ' ' + ' '.join(markov_message))

            markov_message.append(previous_message)

    return context.updated(result=context.result + ' ' + ' '.join(markov_message))


@command(name='m3', hidden=False)
async def generate_markov3(context: MessageContext, client: Client) -> MessageContext:
    if len(context.command.args) != 0:
        return context.updated(result="Currently command does not take any arguments. Sorry 'bout that.")

    markov_message: list[str] = []
    previous_message = Buf(size=2)
    if previous_message.get() == [None, None]:
        with get_db() as db:
            candidates = db.execute(
                select(Markov3),
            ).scalars().all()
            [candidate] = random.choices(candidates, get_markov_weights(candidates))
            previous_message.push(candidate.word3)
            markov_message.append(candidate.word3)
            candidates = db.execute(
                select(Markov3)
                .where(
                    or_(
                        Markov3.word1 == candidate.word3,
                        Markov3.word2 == candidate.word3,
                    ),
                ),
            ).scalars().all()
            [candidate] = random.choices(candidates, get_markov_weights(candidates))
            previous_message.push(candidate.word3)
            markov_message.append(candidate.word3)
            markov_message = [w for w in markov_message if w is not None]

    with get_db() as db:
        while True:
            candidates = db.execute(
                select(Markov3)
                .where(
                    Markov3.word1 == previous_message.get()[0],
                    Markov3.word2 == previous_message.get()[1],
                ),
            ).scalars().all()

            if len(candidates) == 0:
                return context.updated(result=context.result + ' ' + ' '.join(markov_message))

            [candidate] = random.choices(candidates, get_markov_weights(candidates))
            if candidate is None or candidate.word3 is None:
                return context.updated(result=context.result + ' ' + ' '.join(markov_message))

            previous_message.push(candidate.word3)
            if previous_message is None or len(' '.join(markov_message + [previous_message.last])) > DISCORD_MESSAGE_LIMIT:
                return context.updated(result=context.result + ' ' + ' '.join(markov_message))

            markov_message.append(previous_message.last)

    return context.updated(result=context.result + ' ' + ' '.join(markov_message))


@command(name='addcmd', hidden=False, special=True)
async def add_command(context: MessageContext, client: Client) -> MessageContext:
    if len(context.command.args) == 0:
        return context.updated(result=f'Usage: `{client.prefix}updatecmd <command_name>`')
    cmd_name = context.command.args[0]
    try:
        with get_db() as db:
            db.add(
                CommandModel(
                    name=cmd_name,
                    command=context.command.raw_args.split(' ', maxsplit=1)[1],
                ),
            )
            db.commit()
    except Exception as e:
        return context.updated(result=str(e))
    return context.updated(result=f'Command `{cmd_name}` added')


@command(name='updatecmd', hidden=False, special=True)
async def update_command(context: MessageContext, client: Client) -> MessageContext:
    if len(context.command.args) == 0:
        return context.updated(result=f'Usage: `{client.prefix}updatecmd <command_name>`')
    cmd_name = context.command.args[0]
    try:
        with get_db() as db:
            result = db.execute(
                update(CommandModel)
                .where(CommandModel.name == cmd_name)
                .values(command=context.command.raw_args.split(' ', maxsplit=1)[1]),
            )
            db.commit()
            if result.rowcount == 0:  # type: ignore
                return context.updated(result=f'Command `{cmd_name}` not found')
    except Exception as e:
        return context.updated(result=str(e))
    return context.updated(result=f'Command `{cmd_name}` updated')


@command(name='delcmd', hidden=False, special=True)
async def delete_command(context: MessageContext, client: Client) -> MessageContext:
    if len(context.command.args) != 1:
        return context.updated(result=f'Usage: `{client.prefix}updatecmd <command_name>`')
    cmd_name = context.command.args[0]
    try:
        with get_db() as db:
            db.execute(
                delete(CommandModel)
                .where(CommandModel.name == cmd_name),
            )
            db.commit()
    except Exception as e:
        return context.updated(result=str(e))
    return context.updated(result=f'Command `{cmd_name}` deleted')


@command(name='showcmd', hidden=False, special=True)
async def show_command(context: MessageContext, client: Client) -> MessageContext:
    if len(context.command.args) != 1:
        return context.updated(result=f'Usage: `{client.prefix}updatecmd <command_name>`')
    cmd_name = context.command.args[0]
    try:
        if cmd_name in COMMANDS:
            return context.updated(result=f'Command `{cmd_name}` is builtin')
        with get_db() as db:
            command = db.execute(
                select(CommandModel)
                .where(CommandModel.name == cmd_name),
            ).scalar_one_or_none()
            if command is not None:
                return context.updated(result=f'Command `{cmd_name}` is defined as: `{command.command}`')
            else:
                return context.updated(result=f'Command `{cmd_name}` is not defined')
    except Exception as e:
        return context.updated(result=str(e))


@command(name='set', hidden=False, special=True)
async def set_variable(context: MessageContext, client: Client) -> MessageContext:
    if len(context.command.args) < 2:
        return context.updated(result=f'Usage: `{client.prefix}set <variable_name> <value>`')
    try:
        var_name, var_value = context.command.raw_args.split(' ', maxsplit=1)
        with get_db() as db:
            result = db.execute(
                update(VariableModel)
                .where(VariableModel.name == var_name)
                .values(value=context.command.raw_args.split(' ', maxsplit=1)[1]),
            )
            db.commit()
            if result.rowcount == 0:  # type: ignore
                db.add(
                    VariableModel(
                        name=var_name,
                        value=var_value,
                    ),
                )
                db.commit()
        return context.updated(result=f'Variable `{var_name}` set to {var_value}')

    except Exception as e:
        return context.updated(result=str(e))
