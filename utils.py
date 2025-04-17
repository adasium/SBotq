from __future__ import annotations

import itertools
import random
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pendulum
from sqlalchemy import and_
from sqlalchemy import update

from carrotson import split_into_paths
from database import get_db
from models import Carrot
from models import Markov2
from models import Markov3


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
    if result == 0:
        return '0'
    decimal_part = str(result).split('.')[1]
    first_nonzero_pos = next((i for i, digit in enumerate(decimal_part) if digit != '0'), None)
    precision = first_nonzero_pos + 1
    return f'{result:.{precision}f}'



def _markovify2(
    *,
    text: str,
    channel_id: int,
    guild_id: int,
) -> None:
    parts = text.split()
    with get_db() as db:
        for word1, word2 in window([None] + parts + [None], n=2):
            result = db.execute(
                update(Markov2)
                .where(
                    and_(
                        Markov2.word1 == word1,
                        Markov2.word2 == word2,
                        Markov2.channel_id == channel_id,
                        Markov2.guild_id == guild_id,
                    ),
                )
                .values(counter=Markov2.counter + 1),
            )
            if result.rowcount == 0:  # type: ignore
                db.add(
                    Markov2(
                        word1=word1,
                        word2=word2,
                        channel_id=channel_id,
                        guild_id=guild_id,
                    ),
                )
        db.commit()


def _markovify3(
    *,
    text: str,
    channel_id: int,
    guild_id: int,
) -> None:
    parts = text.split()
    with get_db() as db:
        for word1, word2, word3 in window([None] + parts + [None], n=3):
            result = db.execute(
                update(Markov3)
                .where(
                    and_(
                        Markov3.word1 == word1,
                        Markov3.word2 == word2,
                        Markov3.word3 == word3,
                        Markov3.channel_id == channel_id,
                        Markov3.guild_id == guild_id,
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
                        channel_id=channel_id,
                        guild_id=guild_id,
                    ),
                )
        db.commit()


def _carrot(
    *,
    text: str,
    channel_id: int,
    guild_id: int,
) -> None:
    with get_db() as db:
        for path in split_into_paths(text):
            result = db.execute(
                update(Carrot)
                .where(
                    and_(
                        Carrot.context == path.context,
                        Carrot.following == path.following,
                        Carrot.channel_id == channel_id,
                        Carrot.guild_id == guild_id,
                    ),
                )
                .values(counter=Carrot.counter + 1),
            )
            if result.rowcount == 0:  # type: ignore
                db.add(
                    Carrot(
                        context=path.context,
                        following=path.following,
                        channel_id=channel_id,
                        guild_id=guild_id,
                    ),
                )
        db.commit()


def markovify(
    *,
    text: str,
    channel_id: int,
    guild_id: int,
    markov2: bool = False,
    markov3: bool = False,
    carrot: bool = False,
) -> None:
    if markov2:
        _markovify2(
            text=text,
            channel_id=channel_id,
            guild_id=guild_id,
        )
    if markov3:
        _markovify3(
            text=text,
            channel_id=channel_id,
            guild_id=guild_id,
        )
    if carrot:
        _carrot(
            text=text,
            channel_id=channel_id,
            guild_id=guild_id,
        )
