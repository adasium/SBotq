from __future__ import annotations

import functools
from datetime import datetime

import pendulum


@functools.total_ordering
class Bernardynki:
    FIRST_WHEN = pendulum.DateTime(2022, 1, 16, tzinfo=pendulum.UTC)

    def __init__(self, when: pendulum.DateTime, count: int = 1) -> None:
        self.when = when
        self.count = count

    @property
    def great(self) -> bool:
        b = self.FIRST_WHEN
        while b < self.when:
            b = b.add(years=1, months=1)
        return (b.year, b.month) == (self.when.year, self.when.month)

    @property
    def ordinal(self) -> int:
        return (self.count - 1) % 13 + 1

    @property
    def year(self) -> int:
        return (self.count - 1) // 13 + 1

    def __add__(self, other: object) -> Bernardynki:
        if isinstance(other, int):
            b = self
            for _ in range(other):
                b = Bernardynki(
                    when=b.when.add(months=1, days=1),
                    count=b.count + 1,
                )
            return b
        else:
            return NotImplemented

    def __iadd__(self, other: object) -> Bernardynki:
        if isinstance(other, int):
            for _ in range(other):
                self = self + 1
            return self
        else:
            return NotImplemented

    def __lt__(self, other: object) -> Bernardynki:
        if isinstance(other, datetime):
            return self.when.date() < other.date()
        else:
            return NotImplemented

    def __eq__(self, other: object) -> Bernardynki:
        if isinstance(other, datetime):
            return self.when.date == other.when.date
        else:
            return NotImplemented

    def __repr__(self) -> str:
        return f'{self.ordinal}th of year {self.year} ({self.count}) ({self.when.date()}) {"GREAT" if self.great else ""}'

    @classmethod
    @property
    def first(cls) -> Bernardynki:
        return Bernardynki(
            when=cls.FIRST_WHEN,
        )
