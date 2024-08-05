from __future__ import annotations

import itertools
import random
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from typing import Any
from typing import Callable

import pendulum

from models import Markov2
from models import Markov3
from settings import DEFAULT_PREFIX


def time_difference(time1: time, time2: time) -> timedelta:
    t1 = datetime(1990, 1, 1, time1.hour, time1.minute)
    t2 = datetime(1990, 1, 1, time2.hour, time2.minute)
    if t2 > t1:
        return t2 - t1
    else:
        return t2 + timedelta(days=1) - t1


def window(seq, n=2):
    """
    Returns a sliding window (of width n) over data from the iterable
    s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...
    """

    it = iter(seq)
    result = tuple(itertools.islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


def shuffle_str(s: str) -> str:
    stringlist = list(s)
    random.shuffle(stringlist)
    return ''.join(stringlist)


def get_markov_weights(markovs: list[Markov2 | Markov3]) -> list[float]:
    total = sum(markov.counter for markov in markovs)
    return [markov.counter / total for markov in markovs]


class Buf:
    def __init__(self, size: int = 2) -> None:
        self._buf = [None] * size
        self.size = size

    def push(self, value) -> None:
        self._buf = (self._buf + [value])[-self.size:]

    def get(self) -> list:
        return self._buf

    @property
    def last(self) -> Any:
        return self._buf[-1]


def is_special_command(
        full_message_content: str,
        commands: dict[str, Callable],
        special_commands: dict[str, Callable],
        prefix: str = DEFAULT_PREFIX,
) -> bool:
    cmd_name = remove_prefix(text=full_message_content, prefix=prefix).split(' ')[0]
    return cmd_name in commands and cmd_name in special_commands


def remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def triggered_chance(percentage_chance: float) -> bool:
    return random.random() < percentage_chance


def next_call_timestamp(
    now: pendulum.DateTime,
    scheduled_at: time,
    scheduled_every: pendulum.Duration,
) -> pendulum.DateTime:
    candidate = now.replace(hour=scheduled_at.hour, minute=scheduled_at.minute)
    while candidate < now:
        candidate += scheduled_every
    return candidate


def format_fraction(numerator: int, denominator: int) -> str:
    result = Decimal(numerator) / Decimal(denominator)
    decimal_part = str(result).split('.')[1]
    first_nonzero_pos = next((i for i, digit in enumerate(decimal_part) if digit != '0'), None)
    precision = first_nonzero_pos + 1
    return f'{result:.{precision}f}'
