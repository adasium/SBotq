from __future__ import annotations

import random
from functools import wraps
from typing import Awaitable
from typing import Callable
from typing import TYPE_CHECKING

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
    return context.updated('pong')


@command(name='bing')
async def bing(context: MessageContext, client: Client) -> MessageContext:
    return context.updated('bong')


@command(name='commands')
async def commands(context: MessageContext, client: Client) -> MessageContext:
    prefix = client.prefix
    result = ', '.join(f'{prefix}{command}' for command in sorted(COMMANDS))
    return context.updated(result)


@command(name='version')
async def version(context: MessageContext, client: Client) -> MessageContext:
    if random.random() < 0.5:
        return context.updated('69')
    else:
        return context.updated('420')


@command(name='random')
async def random_(context: MessageContext, client: Client) -> MessageContext:
    try:
        cmd, *args = context.result.removeprefix(client.prefix).split()
        if len(args) == 0:
            return context.updated(str(random.random()))
        elif len(args) == 1:
            return context.updated(str(random.randint(0, int(args[0]))))
        elif len(args) == 2:
            return context.updated(str(random.randint(int(args[0]), int(args[1]))))
        return context.updated('Co za dużo to niezdrowo')
    except ValueError as e:
        return context.updated(str(e))
    return context.updated('Coś ty narobił')


@command(name='upper')
async def upper(context: MessageContext, client: Client) -> MessageContext:
    return context.updated(context.result.upper())
