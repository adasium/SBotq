from __future__ import annotations

import asyncio
import io
import random
import textwrap
from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import Generator
from typing import Optional
from typing import Protocol

import discord
import pandas as pd
import pendulum
import requests
from PIL import Image
from sqlalchemy import delete
from sqlalchemy import desc
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update

import diffle
from bernardynki import Bernardynki
from botka_script.utils import interpret_source
from carrotson import CONTEXT_SIZE
from command import Command
from database import get_db
from decorators import daily
from decorators import run_every
from difflanek import difflanek
from difflanek import opencv
from exceptions import CommandNotFound
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
from settings import DEFAULT_PREFIX
from settings import DISCORD_MESSAGE_LIMIT
from settings import MARKOV_MIN_WORD_COUNT
from settings import RANDOM_MARKOV_MESSAGE_CHANCE
from settings import RANDOM_MARKOV_MESSAGE_COUNT
from utils import Buf
from utils import format_fraction
from utils import get_markov_weights
from utils import markovify
from utils import shuffle_str
from utils import triggered_chance


class CommandFunc(Protocol):
    def __call__(self, context: MessageContext, client: discord.Client) -> Awaitable[MessageContext]: ...


logger = get_logger(__name__)

COMMANDS = {}
HIDDEN_COMMANDS = {}
SPECIAL_COMMANDS = {}


def parse_pipe(message: str, prefix: str = DEFAULT_PREFIX) -> list[Command]:
    ret = []
    cmds = _parse_commands(message, prefix)
    for cmd in cmds:
        if get_builtin_command(cmd.name):
            ret.append(cmd)
            continue

        custom_cmd = get_custom_command(cmd.name)
        if custom_cmd is not None:
            ret.extend(custom_cmd)
            continue
        raise CommandNotFound(cmd.name)

    return ret


def _parse_commands(message: str, prefix: str = DEFAULT_PREFIX) -> List[Command]:
    def _split_by_pipe(message: str) -> Generator[str, None, None]:
        buf = ''
        escaped = False
        while True:
            if len(message) == 0:
                if escaped:
                    raise ValueError('did not find closing ```')
                if buf:
                    yield buf
                return None
            if message.startswith('```'):
                buf += message[:3]
                message = message[3:]
                escaped = not escaped
                continue
            if message.startswith('||'):
                buf += message[:2]
                message = message[2:]
                continue
            if message.startswith('|') and not escaped:
                yield buf
                buf = ''
                message = message[1:]
                continue

            buf += message[0]
            message = message[1:]

    parts = list(_split_by_pipe(message))
    commands = [Command.from_str(part.lstrip(), prefix) for part in parts]
    return commands


def get_builtin_command(cmd_name: str) -> CommandFunc | None:
    return COMMANDS.get(cmd_name)


def get_custom_command(cmd_name: str) -> list[Command] | None:
    with get_db() as db:
        command = db.execute(
            select(CommandModel)
            .where(CommandModel.name == cmd_name),
        ).scalar_one_or_none()
    if command is None:
        return None
    return parse_pipe(command.command, prefix=DEFAULT_PREFIX)


def get_command(cmd_name: str) -> CommandFunc | CommandModel | None:
    cmd = get_builtin_command(cmd_name)
    if cmd is None:
        cmd = get_custom_command(cmd_name)
    if cmd is None:
        return None
    return cmd


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

    markovify(
        text=context.message.content,
        channel_id=context.message.channel.id,
        guild_id=context.message.guild.id,
        markov2=True,
    )
    return context


@command(name='markov3', hidden=True)
async def markov3(context: MessageContext, client: discord.Client) -> MessageContext:
    parts = context.message.content.split()
    if len(parts) < 3:
        return context

    markovify(
        text=context.message.content,
        channel_id=context.message.channel.id,
        guild_id=context.message.guild.id,
        markov3=True,
    )
    return context


async def carrot(context: MessageContext, client: discord.Client) -> MessageContext:
    markovify(
        text=context.message.content,
        channel_id=context.message.channel.id,
        guild_id=context.message.guild.id,
        carrot=True,
    )
    return context


@command(name='inspire')
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
            await markov2(MessageContext(original_message=message), client)
            await markov3(MessageContext(original_message=message), client)
    logger.debug('DONE TRAINING ON CHANNEL %s', context.message.channel)
    return context


@command(name='train_carrot')
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
            await carrot(MessageContext(original_message=message), client)
    logger.debug('DONE TRAINING ON CHANNEL %s', context.message.channel)
    return context


@command(name='m')
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


@command(name='m3')
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


def generate_carrot_from_context(msg_context: str) -> str:
    with get_db() as db:
        while len(msg_context) < DISCORD_MESSAGE_LIMIT:
            candidates = _get_carrot_candidates(db, context=msg_context[-CONTEXT_SIZE:] if msg_context else '')
            if not candidates:
                return msg_context

            random.shuffle(candidates)
            if 0 < len(msg_context) < CONTEXT_SIZE:
                msg_context = candidates[0].context + candidates[0].following
            else:
                msg_context += candidates[0].following
    return msg_context


@command(name='carrot')
async def generate_carrot(context: MessageContext, client: discord.Client) -> MessageContext:
    msg_context = context.command.raw_args
    msg_context = generate_carrot_from_context(msg_context)
    return context.updated(result=msg_context)


@command(name='addcmd', special=True)
async def add_command(context: MessageContext, client: discord.Client) -> MessageContext:
    if len(context.command.args) == 0:
        return context.updated(result=f'Usage: `{client.prefix}addcmd <command_name> <instructions>`')
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


@command(name='updatecmd', special=True)
async def update_command(context: MessageContext, client: discord.Client) -> MessageContext:
    if len(context.command.args) == 0:
        return context.updated(result=f'Usage: `{client.prefix}updatecmd <command_name> <instructions>`')
    cmd_name = context.command.args[0]
    try:
        new_cmd_value = context.command.raw_args.split(' ', maxsplit=1)[1]
        commands = parse_pipe(new_cmd_value, prefix=client.prefix)
        commands_str = ' | '.join(
            cmd.to_str()
            for cmd in commands
        )
        with get_db() as db:
            result = db.execute(
                update(CommandModel)
                .where(CommandModel.name == cmd_name)
                .values(command=commands_str),
            )
            db.commit()
            if result.rowcount == 0:  # type: ignore
                return context.updated(result=f'Command `{cmd_name}` not found')
    except Exception as e:
        return context.updated(result=str(e))
    return context.updated(result=f'Command `{cmd_name}` updated')


@command(name='delcmd', special=True)
async def delete_command(context: MessageContext, client: discord.Client) -> MessageContext:
    if len(context.command.args) != 1:
        return context.updated(result=f'Usage: `{client.prefix}delcmd <command_name>`')
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


@command(name='showcmd', special=True)
async def show_command(context: MessageContext, client: discord.Client) -> MessageContext:
    if len(context.command.args) != 1:
        return context.updated(result=f'Usage: `{client.prefix}showcmd <command_name>`')
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
                cmd_display = command.command.replace('`', '\\`')
                return context.updated(result=f'Command `{cmd_name}` is defined as: ```{cmd_display}\n```')
            else:
                return context.updated(result=f'Command `{cmd_name}` is not defined')
    except Exception as e:
        return context.updated(result=str(e))


@command(name='set', special=True)
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


@run_every(days=1, condition=lambda dt: (Bernardynki.next_after(dt).when - dt).in_days() in (7, 3, 1, 0))
@command(name='next_bernardynki', special=True)
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

    sign = '+'
    offset = context.command.raw_args.strip()
    if offset.startswith(('-', '+')):
        sign, offset = offset[0], offset[1:]
    try:
        offset = int(offset)
    except ValueError:
        offset = 0
    if sign == '+':
        next_bernardynki += offset
    else:
        next_bernardynki -= offset

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


@command(name='suggest')
async def suggest(context: MessageContext, client: discord.Client) -> MessageContext:
    await context.message.add_reaction('⬆️')
    await context.message.add_reaction('⬇️')
    return context


@command(name='yywrap')
async def yywrap(context: MessageContext, client: discord.Client) -> MessageContext:
    logger.debug('yy > %s', context.command.raw_args)
    source = context.command.raw_args
    if source.startswith('```'):
        source = source[3:]
    if source.endswith('```'):
        source = source[:-3]

    if not source:
        return context.updated(
            result=textwrap.dedent(f'''
            ```
            yywrap - wykonywacz kodu źródłowego

            użycie: {client.prefix}yywrap <SOURCE_CODE>

            przykład: {client.prefix}yywrap (message "XD")
            przykład: {client.prefix}yywrap (message (2+2))
            ```'''),
        )

    extra = {
        'current_message_context': context.result,
    }
    if context.message.reference is not None:
        referenced_message = await context.message.channel.fetch_message(context.message.reference.message_id)
        extra['referenced_message'] = referenced_message.content
    result = interpret_source(
        source,
        **extra,
        exc=Exception,
    )
    logger.debug('yy > %s', result)
    if result.success:
        await context.message.add_reaction('✔️')
        return context.updated(result=result.stdout)
    else:
        await context.message.add_reaction('❌')
        return context.updated(result=result.stderr)


@command(name='dfl')
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
    if context.command.raw_args:
        params = [p for p in context.command.raw_args.split(' ') if p]

        is_polish_word = params[0] == 'pl'
        words = params[int(is_polish_word):]

        result_all = sorted(filter(lambda x: len(x) >= 3, difflanek.find_solution(words, is_polish_word)))
        n = 50
        if len(result_all) > n:
            result = sorted(set(random.sample(result_all, n)))
        else:
            result = result_all

        dict_size = difflanek.get_total_count()
        percentage = format_fraction(100 * len(result_all), dict_size)
        message = f'{len(result)}/{len(result_all)} | {percentage}%: {result}'
        context = context.updated(result=message[:2000], input=result_all)
        return context
    else:
        return context.updated(result=difflanek.get_help())


@command(name='rand')
async def _rand(context: MessageContext, client: discord.Client) -> MessageContext:
    help = '''\
```
!rand <a> [b [c [d ...]]]
!echo a b c d | !rand
```
'''
    if context.input is not None and isinstance(context.input, list):
        return context.updated(result=random.choice(context.input))

    target = (context.result or context.command.raw_args).split()
    if target:
        return context.updated(result=random.choice(target))
    else:
        return context.updated(result=help)


@command(name='all')
async def _all(context: MessageContext, client: discord.Client) -> MessageContext:
    if context.input is not None and isinstance(context.input, list):
        input_str = str(context.input)
        if len(input_str) <= DISCORD_MESSAGE_LIMIT:
            return context.updated(result=input_str)
        else:
            with io.BytesIO() as buf:
                buf.write(
                    '\n'.join(context.input).encode('utf8'),
                )
                buf.seek(0)
                context.attachment = discord.File(fp=buf, filename='all.txt')
                return context
    return context


@command(name='dflocr')
async def _dflocr(context: MessageContext, client: discord.Client) -> MessageContext:
    if context.message.reference is None:
        return context.updated(result='You need to respond to a message with an image')

    referenced_message = await context.message.channel.fetch_message(context.message.reference.message_id)
    for attachment in referenced_message.attachments:
        ct = attachment.content_type
        if ct and ct.startswith('image'):
            logger.debug('Found image with type: %s', ct)
            image = await attachment.read()
            try:
                dfl = opencv.get_difflanek(image)
            except opencv.DifflanekException:
                return context.updated(result='no rectangles found')
            else:
                return context.updated(result=' '.join(dfl))
    return context.updated(result='no images found')


@command(name='przeczytaj')
async def _read_attachment(context: MessageContext, client: discord.Client) -> MessageContext:
    if context.message.reference is None:
        return context.updated(result='You need to respond to a message with that command')
    referenced_message = await context.message.channel.fetch_message(context.message.reference.message_id)
    await referenced_message.add_reaction('📖')
    nothing_to_read = True
    for attachment in referenced_message.attachments:
        ct = attachment.content_type
        if not ct:
            continue
        if not ct.startswith('text'):
            continue
        logger.debug('Found text with type: %s', ct)
        nothing_to_read = False
        text_bytes = await attachment.read()
        text = text_bytes.decode('utf8')
        markovify(
            text=text,
            channel_id=context.message.channel.id,
            guild_id=context.message.guild.id,
            markov2=True,
            markov3=True,
            carrot=True,
        )
    await referenced_message.remove_reaction('📖', client.user)
    if nothing_to_read:
        return context.updated(result='nothing to read')
    await referenced_message.add_reaction('🤔')
    text_review = generate_carrot_from_context(text[:8])
    await referenced_message.remove_reaction('🤔', client.user)
    return context.updated(result=text_review)


@command(name='d20')
async def _d20(context: MessageContext, client: discord.Client) -> MessageContext:
    roll = random.randint(1, 20)
    n1 = roll // 10
    n2 = roll % 10
    return context.updated(
        result="""\
```
     _._
   _/ | \_
 _/---^---\_
|_   /{n1}\   _|
| \ / {n2} \ / |
|__/_____\__|
 ^-_\   /_-^
    ^-v-^
```
""".format(n1=roll // 10 or ' ', n2=roll % 10),
    )
