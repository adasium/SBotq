from __future__ import annotations

import os
from typing import Callable
from typing import overload
from typing import Type
from typing import TypeVar


ENV_FILE_COMMENT = '#'

T = TypeVar('T')

_MISSING = object()


@overload
def getenv(name: str, *, default: str = None) -> str: ...
@overload
def getenv(name: str, *, as_: Type[bool], default: bool) -> bool: ...
@overload
def getenv(name: str, *, as_: Type[str] = str, default: str) -> str: ...
@overload
def getenv(name: str, *, as_: Callable[[str], T]) -> T: ...


def getenv(
        name: str,
        *,
        as_: Callable[[str], T] | Type[bool] | Type[str] = str,
        default: T | bool | str | None = None,
) -> T | bool | str:
    if os.environ.get(name, _MISSING) == _MISSING and default is not None:
        return default

    value = os.environ[name]
    if isinstance(as_, type) and issubclass(as_, bool):
        if value.lower() in ('false', ''):
            return False
        else:
            return True
    return as_(value)


def load_env_file(path: str = '.env') -> None:
    try:
        with open(path) as f:
            for line in f:
                if line.startswith(ENV_FILE_COMMENT):
                    continue
                key, value = [item.strip() for item in line.split('=', maxsplit=1)]
                os.environ[key] = value
    except IOError as e:
        print(e)


load_env_file()
