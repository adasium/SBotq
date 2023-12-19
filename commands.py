from typing import Awaitable
from typing import TypeVar
import discord
from typing import Callable
from functools import wraps
from message_context import MessageContext


COMMANDS = {}
T = TypeVar('T')
CommandFunc = Callable[[MessageContext, discord.Client], Awaitable[MessageContext]]


def command(*, name: str) -> Callable[[CommandFunc], CommandFunc]:
    def decorator(func: CommandFunc) -> CommandFunc:
        @wraps(func)
        async def wrapper(context: MessageContext, client: discord.Client) -> MessageContext:
            return await func(context, client)
        COMMANDS[name] = wrapper
        return wrapper
    return decorator


@command(name='ping')
async def ping(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated('pong')


@command(name='bing')
async def bing(context: MessageContext, client: discord.Client) -> MessageContext:
    return context.updated('bong')
