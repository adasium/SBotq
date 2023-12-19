from __future__ import annotations

import os
from typing import Callable
from typing import overload
from typing import Type
from typing import TypeVar

from command import Command
from settings import DEFAULT_PREFIX


T = TypeVar('T')
U = TypeVar('U')


def _ident(v: str) -> str:
    return v


@overload
def getenv(name: str) -> str: ...
@overload
def getenv(name: str, as_: Type[bool]) -> bool: ...
@overload
def getenv(name: str, as_: Type[str] = str) -> str: ...
@overload
def getenv(name: str, as_: Callable[[str], T]) -> T: ...


def getenv(name: str, as_: Callable[[str], T] | Type[bool] | Type[str] = str) -> T | bool | str:
    value = os.environ[name]
    if isinstance(as_, type) and issubclass(as_, bool):
        if value.lower() in ('false', ''):
            return False
        else:
            return True
    return as_(value)


def parse_commands(message: str, prefix: str = DEFAULT_PREFIX) -> list[Command]:
    parts = [p.strip() for p in message.split('|')]
    return [Command.from_str(part) for part in parts]
