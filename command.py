from __future__ import annotations

from typing import List
from typing import NamedTuple

from settings import DEFAULT_PREFIX
from utils import remove_prefix


class Command(NamedTuple):
    name: str
    raw_args: str
    args: list[str]

    @classmethod
    def from_str(cls, s: str, prefix: str = DEFAULT_PREFIX) -> 'Command':
        if not s.startswith(prefix):
            raise ValueError
        stripped = remove_prefix(text=s, prefix=prefix)
        cmd_name, *raw_args = [part.strip() for part in stripped.split(' ', maxsplit=1)]
        _, *args = [part.strip() for part in stripped.split()]

        return Command(
            name=cmd_name,
            raw_args=''.join(raw_args),
            args=args,
        )

    @classmethod
    def dummy(cls) -> 'Command':
        return Command(
            name='привет',
            raw_args='',
            args=[],
        )


def parse_commands(message: str, prefix: str = DEFAULT_PREFIX) -> List[Command]:
    parts = [p.strip() for p in message.split(' | ')]
    return [Command.from_str(part) for part in parts]
