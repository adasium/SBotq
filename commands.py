from __future__ import annotations

import random
from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import TYPE_CHECKING

from logger import logger
from message_context import MessageContext

if TYPE_CHECKING:
    from client import Client
    CommandFunc = Callable[[MessageContext, Client], Awaitable[MessageContext]]


COMMANDS = {}


def command(*, name: str) -> Callable[[CommandFunc], CommandFunc]:
    def decorator(func: CommandFunc) -> CommandFunc:
        @wraps(func)
        async def wrapper(context: MessageContext, client: Client) -> MessageContext:
            return await func(context, client)
        COMMANDS[name] = wrapper
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


@command(name='version')
async def version(context: MessageContext, client: Client) -> MessageContext:
    if random.random() < 0.5:
        return context.updated(result='69')
    else:
        return context.updated(result='420')


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
    if (cmd := context.command) is not None:
        return context.updated(result=cmd.raw_args)
    return context


@command(name='scream')
async def scream(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(result=context.result.upper())
