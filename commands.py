from __future__ import annotations

import asyncio
import io
import random
from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Protocol

import discord
import pandas as pd
import pendulum
import requests
from PIL import Image
from sqlalchemy import and_
from sqlalchemy import delete
from sqlalchemy import desc
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update

import diffle
from bernardynki import Bernardynki
from botka_script.expr import interpret
from carrotson import CONTEXT_SIZE
from carrotson import split_into_paths
from database import get_db
from decorators import daily
from decorators import run_every
from difflanek import difflanek
from exceptions import DiscordMessageMissingException
from getenv import getenv
from logger import get_logger
from message_context import MessageContext
from models import Carrot
from models import CommandModel
from models import Markov2
from models import Markov3
from models import VariableModel
from settings import COMMON_PREFIXES
from settings import DISCORD_MESSAGE_LIMIT
from settings import MARKOV_MIN_WORD_COUNT
from settings import RANDOM_MARKOV_MESSAGE_CHANCE
from settings import RANDOM_MARKOV_MESSAGE_COUNT
from utils import Buf
from utils import get_markov_weights
from utils import shuffle_str
from utils import triggered_chance
from utils import window


class CommandFunc(Protocol):
    def __call__(self, context: MessageContext, client: discord.Client) -> Awaitable[MessageContext]: ...


logger = get_logger(__name__)

COMMANDS = {}
HIDDEN_COMMANDS = {}
SPECIAL_COMMANDS = {}


def command(*, name: str, hidden: bool = False, special: bool = False) -> Callable[[CommandFunc], CommandFunc]:
    def decorator(func: CommandFunc) -> CommandFunc:
        @wraps(func)
        async def wrapper(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def ping(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated(result='pong')


@command(name='bing')
async def bing(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated(result='bong')


@command(name='commands')
async def commands(context: MessageContext, client: discord.Client) -> MessageContext:
    prefix = client.prefix
    result = ', '.join(f'{prefix}{command}' for command in sorted(COMMANDS))
    return context.updated(result=result)


@command(name='random')
async def random_(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def echo(context: MessageContext, client: discord.Client) -> MessageContext:
    if context.command.raw_args:
        content = context.command.raw_args
    else:
        content = ' '.join([context.result] * 2)
    return context.updated(result=content)


@command(name='scream')
async def scream(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated(result=context.result.upper())


@command(name='shrug')
async def shrug(context: MessageContext, client: discord.Client) -> MessageContext:
    if context.command.raw_args:
        content = context.command.raw_args
    else:
        content = context.result
    result = rf'¯\\\_{content}_/¯'
    return context.updated(result=result)


@command(name='shuffle_words')
async def shuffle_words(context: MessageContext, client: discord.Client) -> MessageContext:
    if context.command.raw_args:
        content = context.command.raw_args
    else:
        content = context.result
    return context.updated(result=' '.join(shuffle_str(word) for word in content.split()))


@command(name='chid')
async def chid(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated(result=str(context.message.channel.id))


@command(name='myid')
async def myid(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated(result=str(context.message.author.id))


@command(name='markov2', hidden=True)
async def markov2(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def markov3(context: MessageContext, client: discord.Client) -> MessageContext:
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


async def carrot(context: MessageContext, client: discord.Client) -> MessageContext:
    with get_db() as db:
        for path in split_into_paths(context.message.content):
            result = db.execute(
                update(Carrot)
                .where(
                    and_(
                        Carrot.context == path.context,
                        Carrot.following == path.following,
                        Carrot.channel_id == context.message.channel.id,
                        Carrot.guild_id == context.message.guild.id,
                    ),
                )
                .values(counter=Carrot.counter + 1),
            )
            if result.rowcount == 0:  # type: ignore
                db.add(
                    Carrot(
                        context=path.context,
                        following=path.following,
                        channel_id=context.message.channel.id,
                        guild_id=context.message.guild.id,
                    ),
                )
        db.commit()
    return context


@command(name='inspire', hidden=False)
async def inspire(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def daily_inspiration(context: MessageContext, client: discord.Client) -> MessageContext:
    channel = client.get_channel(getenv('INSPIRATIONAL_MESSAGE_CHANNEL_ID', as_=int))
    await channel.send('Miłego dnia i smacznej kawusi <3')
    await inspire(context=context, client=client)  # type: ignore
    return context


@command(name='train_markov', hidden=True)
async def train_markov(context: MessageContext, client: discord.Client) -> MessageContext:
    i = 1
    async for message in context.message.channel.history(limit=None):
        i += 1
        logger.debug('Training on channel %s: message no %s', message.channel, i)
        if (
                message.author != client.user
                and not message.content.startswith(client.prefix)
                and len(message.content.split()) > MARKOV_MIN_WORD_COUNT
        ):
            await markov2(MessageContext(discord_message=message), client)
            await markov3(MessageContext(discord_message=message), client)
    logger.debug('DONE TRAINING ON CHANNEL %s', context.message.channel)
    return context


@command(name='train_carrot', hidden=False)
async def train_carrot(context: MessageContext, client: discord.Client) -> MessageContext:
    i = 1
    async for message in context.message.channel.history(limit=None):
        i += 1
        logger.debug('Training on channel %s: message no %s', message.channel, i)
        if (
                message.author != client.user
                and not message.content.startswith((client.prefix, *COMMON_PREFIXES))
                and len(message.content) >= CONTEXT_SIZE
        ):
            await carrot(MessageContext(discord_message=message), client)
    logger.debug('DONE TRAINING ON CHANNEL %s', context.message.channel)
    return context


@command(name='m', hidden=False)
async def generate_markov2(context: MessageContext, client: discord.Client) -> MessageContext:
    try:
        markov_message = context.command.args
        previous_message: Optional[str] = context.command.args[-1]
    except (IndexError, DiscordMessageMissingException):
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
async def generate_markov3(context: MessageContext, client: discord.Client) -> MessageContext:
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


def _get_carrot_candidates(db, context: str) -> list[Carrot]:
    is_partial = 0 < len(context) < CONTEXT_SIZE
    candidates = db.execute(
        select(Carrot)
        .where(
            (Carrot.context == context) if not is_partial else Carrot.context.startswith(context),
        )
        .order_by(desc(Carrot.counter)),

    ).scalars().all()
    return candidates


@command(name='carrot', hidden=False)
async def generate_carrot(context: MessageContext, client: discord.Client) -> MessageContext:
    msg_context = context.command.raw_args

    with get_db() as db:
        while len(msg_context) < DISCORD_MESSAGE_LIMIT:
            candidates = _get_carrot_candidates(db, context=msg_context[-CONTEXT_SIZE:] if msg_context else '')
            if not candidates:
                return context.updated(result=msg_context)

            random.shuffle(candidates)
            if 0 < len(msg_context) < CONTEXT_SIZE:
                msg_context = candidates[0].context + candidates[0].following
            else:
                msg_context += candidates[0].following

    return context.updated(result=msg_context)


@command(name='addcmd', hidden=False, special=True)
async def add_command(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def update_command(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def delete_command(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def show_command(context: MessageContext, client: discord.Client) -> MessageContext:
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
async def set_variable(context: MessageContext, client: discord.Client) -> MessageContext:
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


async def generate_markov_at_random_time(context: MessageContext, client: discord.Client) -> None:
    while True:
        await asyncio.sleep(1 * 60)
        with get_db() as db:
            random_markov_chance = db.execute(
                select(VariableModel)
                .where(VariableModel.name == 'RANDOM_MARKOV_CHANCE'),
            ).scalar_one_or_none()
            if random_markov_chance is None:
                random_markov_chance = RANDOM_MARKOV_MESSAGE_CHANCE
            else:
                try:
                    random_markov_chance = float(random_markov_chance.value)
                except ValueError:
                    random_markov_chance = RANDOM_MARKOV_MESSAGE_CHANCE
            if triggered_chance(random_markov_chance):
                random_markov_message_count = db.execute(
                    select(VariableModel)
                    .where(VariableModel.name == 'RANDOM_MARKOV_MESSAGE_COUNT'),
                ).scalar_one_or_none()
                if random_markov_message_count is None:
                    random_markov_message_count = RANDOM_MARKOV_MESSAGE_COUNT
                else:
                    try:
                        random_markov_message_count = int(random_markov_message_count.value)
                    except ValueError:
                        random_markov_message_count = RANDOM_MARKOV_MESSAGE_CHANCE
                for _ in range(random_markov_message_count):
                    markov_message = await generate_markov2(context=MessageContext.empty(), client=client)
                    if triggered_chance(0.5):
                        markov_message = await scream(markov_message, client=client)
                    await client.get_channel(
                        getenv('RANDOM_MARKOV_MESSAGE_CHANNEL_ID', as_=int),
                    ).send(markov_message.result)


@run_every(months=1, days=1, condition=lambda dt: (Bernardynki.next_after(dt).when - dt).in_days() in (7, 3, 1, 0))
@command(name='next_bernardynki', hidden=False, special=True)
async def next_bernardynki(context: MessageContext, client: discord.Client) -> MessageContext:
    now = pendulum.now(pendulum.UTC)
    year_in_words_mapping = {
        1: 'pierwszego',
        2: 'drugiego',
        3: 'trzeciego',
        4: 'czwartego',
        5: 'piątego',
    }

    next_bernardynki = Bernardynki.first
    while next_bernardynki < now:
        next_bernardynki += 1

    date_fmt = next_bernardynki.when.format('dddd DD.MM.YYYY', locale='pl')
    days = next_bernardynki.when.diff(now).in_days()
    year_in_words = year_in_words_mapping[next_bernardynki.year]
    if days == 0:
        days_fmt = 'dzisiaj <3'
    elif days == 1:
        days_fmt = 'jutro!'
    else:
        days_fmt = f'za {days} dni'
    msg = f'{next_bernardynki.ordinal}. bernardynki roku {year_in_words} {days_fmt} ({date_fmt})'
    if context is None:
        await client.get_channel(
            getenv('RANDOM_MARKOV_MESSAGE_CHANNEL_ID', as_=int),
        ).send(msg)
    else:
        return context.updated(result=msg)


@command(name='suggest', hidden=False, special=False)
async def suggest(context: MessageContext, client: discord.Client) -> MessageContext:
    await context.message.add_reaction('⬆️')
    await context.message.add_reaction('⬇️')
    return context


@command(name='yywrap', hidden=False, special=False)
async def yywrap(context: MessageContext, client: discord.Client) -> MessageContext:
    logger.debug('yy > %s', context.command.raw_args)
    result = interpret(context.command.raw_args)
    logger.debug('yy > %s', result)
    return context.updated(result=result)


@command(name='dfl', hidden=False, special=False)
async def dfl(context: MessageContext, client: discord.Client) -> MessageContext:
    _help = """\
```
jak wpisywać słowa:
   szary - x
   żółty - X
   zielony:
       pojedyncze litery - (x)
       sekwencje - (xyz)
       poprawny początek/koniec słowa - [x)yzx(yz]
```
    """
    if len(context.command.args) == 0:
        return context.updated(result=_help)
    guess = context.command.args[0]
    solver = diffle.Solver(diffle.DICT)
    solver.guess(guess)
    try:
        matches = solver.get_matches()
    except diffle.InvalidSyntaxException as e:
        return context.updated(result=str(e))
    df = pd.DataFrame(matches, columns=['match'])
    df.index += 1
    df_str = df.to_string(header=False, max_rows=10)
    if len(df.index) == 0:
        return context.updated(result='0 matches')
    else:
        match_str = '1 match' if len(df.index) == 1 else f'{len(df.index)} matches'
        return context.updated(result=f'{match_str}\n```\n{df_str}\n```')

@command(name='difflanek')
async def _difflanek(context: MessageContext, client: discord.Client) -> MessageContext:
    message = []
    if context.command.raw_args:
        params = [p for p in context.command.raw_args.split(' ') if p]

        is_polish_word = params[0] == 'pl'
        words = params[int(is_polish_word):]

        result = list(filter(lambda x: len(x) >= 3, difflanek.find_solution(words, is_polish_word)))
        message.append(f'Ilość pasujących wyników: {len(result)}')
        message.append('')

        n = 50
        if len(result) > n:
            result = list(set(random.sample(result, n)))
            result.sort()
            message.append(f'Przykładowe {n} wyników:')
            message.append('')

        message.append(str(result))
    else:
        message.append(difflanek.get_help())
    return context.updated(result='\n'.join(message)[:2000])
