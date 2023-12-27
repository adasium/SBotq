# https://github.com/tsoding/Gatekeeper/blob/master/internal/carrotson.go
from __future__ import annotations

from typing import Generator
from typing import NamedTuple


CONTEXT_SIZE = 8


def _sliding_window_iter(string: str) -> Generator[Path, None, None]:
    for i in range(-CONTEXT_SIZE, len(string) - CONTEXT_SIZE):
        j = i if i >= 0 else 0
        yield Path(
            context=string[j:i + CONTEXT_SIZE],
            following=string[i + CONTEXT_SIZE],
        )


class Path(NamedTuple):
    context: str
    following: str

    @property
    def new_context(self) -> str:
        new_context = self.context + self.following
        return new_context[-CONTEXT_SIZE:]


def split_into_paths(message: str) -> list[Path]:
    def _inner():
        for part in _sliding_window_iter(message):
            yield part
    return list(_inner())
