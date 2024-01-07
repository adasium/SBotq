from __future__ import annotations

import re
from enum import Enum
from typing import Generator
from typing import NamedTuple

from logger import get_logger


logger = get_logger(__name__)


class InvalidSyntaxException(Exception):
    pass


def get_dict() -> list[str]:
    def _inner() -> Generator[str, None, None]:
        with open('assets/pl.dic') as f:
            for line in f:
                line = line.strip().lower()
                if len(line) < 2 or len(line) > 17:
                    continue
                yield line
    return sorted(set(_inner()), key=lambda word: (len(word), word))


class ChunkType(Enum):
    GREY = 'GREY'
    YELLOW = 'YELLOW'
    GREEN = 'GREEN'
    LEFT_GREEN = 'LEFT_GREEN'
    RIGHT_GREEN = 'RIGHT_GREEN'
    BOTH_GREEN = 'BOTH_GREEN'
    # it's a filler
    EMPTY = ''

    @classmethod
    @property
    def green(cls) -> list[ChunkType]:
        return [
            cls.GREEN,
            cls.LEFT_GREEN,
            cls.RIGHT_GREEN,
            cls.BOTH_GREEN,
        ]

    @classmethod
    def from_opening_paren(cls, paren: str) -> ChunkType:
        assert paren in '[('
        return {
            '(': ChunkType.GREEN,
            '[': ChunkType.LEFT_GREEN,
        }[paren]

    @classmethod
    def from_closing_paren(cls, paren: str, chunk_type: ChunkType) -> ChunkType:
        assert paren in ')]'
        if chunk_type == chunk_type.GREEN:
            return {
                ')': ChunkType.GREEN,
                ']': ChunkType.RIGHT_GREEN,
            }[paren]
        else:
            return {
                ')': ChunkType.LEFT_GREEN,
                ']': ChunkType.BOTH_GREEN,
            }[paren]


class Chunk(NamedTuple):
    word: str
    type: ChunkType

    def to_regex(self) -> str:
        template = self._get_template()
        return template.format(body=self.word)

    def _get_template(self) -> str:
        return {
            ChunkType.LEFT_GREEN: '^{body}',
            ChunkType.RIGHT_GREEN: '{body}$',
            ChunkType.BOTH_GREEN: '^{body}$',
            ChunkType.EMPTY: '.*',
        }.get(self.type, '{body}')


class Solver:
    def __init__(self, dictionary: list[str]) -> None:
        self._dictionary = dictionary
        self._guesses = []

    def guess(self, guess: str) -> None:
        self._guesses.append(guess)

    def get_matches(self, polish: bool = True) -> list[str]:
        local_dict = self._dictionary
        for guess in self._guesses:
            if not self._validate_parens(guess):
                raise InvalidSyntaxException('Unmatched parens')
            chunks = self._parse_guessed_word(guess)
            regex = ''.join(chunk.to_regex() for chunk in chunks)

            logger.debug('vvv diffle vvv')
            logger.debug(guess)
            logger.debug(chunks)
            logger.debug(regex)
            logger.debug('^^^ diffle ^^^')
            local_dict = list(filter(lambda dict_word: re.match(regex, dict_word), local_dict))
        return local_dict

    def _parse_guessed_word(self, guessed_word: str) -> list[Chunk]:
        chunks = []
        chunk_type = None
        word_chunk = ''
        for char in guessed_word:
            if char in '[(':
                assert chunk_type is None
                chunk_type = ChunkType.from_opening_paren(char)
                continue
            if char in ')]':
                assert chunk_type in ChunkType.green
                chunk_type = ChunkType.from_closing_paren(char, chunk_type)
                chunks.append(Chunk(word_chunk, chunk_type))
                word_chunk = ''
                chunk_type = None
                continue
            if char.isupper():
                assert chunk_type is None
                chunks.append(Chunk(char, ChunkType.YELLOW))
            word_chunk += char
        chunks = self._fill_chunks(chunks)
        return chunks

    def _fill_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        one of the green sides is not anchored fill it with empty chunks (regex: .*)
        """
        if not chunks:
            return []
        new_chunks = []
        for chunk in chunks:
            if chunk.type in (ChunkType.RIGHT_GREEN, ChunkType.GREEN):
                new_chunks.append(Chunk(word='', type=ChunkType.EMPTY))
            if chunk.type in ChunkType.green:
                new_chunks.append(chunk)
            if chunk.type == ChunkType.LEFT_GREEN:
                new_chunks.append(Chunk(word='', type=ChunkType.EMPTY))

        return new_chunks

    def _validate_parens(self, word: str) -> bool:
        count = 0
        for char in word:
            if char in '[(':
                count += 1
            if char in ')]':
                count -= 1
            if count < 0:
                return False
        if count != 0:
            return False
        return True


DICT = get_dict()
