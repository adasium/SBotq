from typing import List

import attr

from botka_script.exceptions import ScannerError
from botka_script.tokens import Token
from botka_script.tokens import TokenType


def find_nth(string: str, substring: str, n: int) -> int | None:
    start = string.find(substring)
    if start < 0:
        return None
    while start >= 0 and n > 1:
        start = string.find(substring, start+len(substring))
        n -= 1
    return start


@attr.s(auto_attribs=True, kw_only=True)
class Scanner:
    source: str
    tokens: List[Token] = attr.Factory(list)
    current: int = 0
    start: int = 0
    line: int = 0
    errors: List[str] = attr.Factory(list)

    def scan_tokens(self) -> None:

        while not self.is_at_end():
            self.start = self.current
            self._scan_token()

        _end_line = self.source[:self.current].count('\n')
        _end_column = find_nth(self.source[:self.current], '\n', n=_end_line)
        if _end_column is None:
            _end_column = self.current
        self.tokens.append(
            Token.from_type(
                type=TokenType.EOF,
                start_line=self.line,
                start_column=_end_column,
            ),
        )

    def is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _scan_token(self) -> None:
        c = self._advance()
        one_char_tokens = {
            '(': TokenType.LEFT_PAREN,
            ')': TokenType.RIGHT_PAREN,
        }
        if c in one_char_tokens:
            self._add_token(one_char_tokens[c])
            return None

        if c == '.' and not self._peek().isdigit():
            self._add_token(TokenType.DOT)
            return None

        if c == '!':
            if self._match('='):
                self._add_token(TokenType.BANG_EQUAL)
            else:
                self._add_token(TokenType.BANG)
            return None

        if c == '=':
            if self._match('='):
                self._add_token(TokenType.EQUAL_EQUAL)
            else:
                self._add_token(TokenType.EQUAL)
            return None

        if c == '<':
            if self._match('='):
                self._add_token(TokenType.LESS_EQUAL)
            else:
                self._add_token(TokenType.LESS)
            return None

        if c == '>':
            if self._match('='):
                self._add_token(TokenType.GREATER_EQUAL)
            else:
                self._add_token(TokenType.GREATER)
            return None

        if c in [' ', '\r', '\t', '\n']:
            return None

        if c == '\n':
            self.line += 1
            return None

        if c == '"':
            self._scan_string()
            return None

        if c.isdigit() or c == '.':
            self._scan_number()
            return None

        self._scan_symbol()
        return None

        self.errors.append(f'Unexpected character: `{c}`')
        raise ScannerError

    def _advance(self) -> str:
        c = self.source[self.current]
        self.current += 1
        return c

    def _add_token(self, token_type: TokenType, literal: object = None) -> None:
        text = self.source[self.start:self.current]
        _start_newline_count = self.source[:self.start].count('\n')
        _end_newline_count = self.source[:self.current].count('\n')

        _start_newline_index = find_nth(self.source[:self.start], '\n', n=_start_newline_count) or 0

        _end_newline_index = find_nth(self.source[:self.current], '\n', n=_end_newline_count) or 0

        _start_column = self.start - _start_newline_index
        _end_column = self.current - _end_newline_index - 1
        self.tokens.append(
            Token.from_type(
                type=token_type,
                lexeme=text,
                literal=literal,
                start_line=_start_newline_count,
                end_line=_end_newline_count,
                start_column=_start_column,
                end_column=_end_column,
            ),
        )

    def _match(self, expected: str) -> bool:
        if self.is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
        return True


    def _peek(self) -> str:
        if self.is_at_end():
            return '\0'
        return self.source[self.current]

    def _scan_string(self) -> None:
        while self._peek() != '"' and not self.is_at_end():
            if self._peek() == '\n':
                self.line += 1
            self._advance()

        if self.is_at_end():
            self.errors.append('Unterminated string')
            return None

        self._advance()

        value = self.source[self.start + 1 : self.current - 1]
        self._add_token(TokenType.STRING, value)

    def _scan_number(self) -> None:
        while self._peek().isdigit():
            self._advance()

        if self._peek() == '.' and self._peek_next().isdigit():
            self._advance()

        while self._peek().isdigit():
            self._advance()

        value = self.source[self.start:self.current]
        if '.' in value:
            self._add_token(TokenType.NUMBER, float(value))
        else:
            self._add_token(TokenType.INTEGER, int(value))

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]

    def _scan_symbol(self) -> None:
        special_characters = '() \n'
        while True:
            if self.is_at_end():
                break
            char = self._peek()
            if char not in special_characters:
                self._advance()
            else:
                break

        value = self.source[self.start:self.current]
        keywords = {
            TokenType.AND.value: TokenType.AND,
            TokenType.CLASS.value: TokenType.CLASS,
            TokenType.ELSE.value: TokenType.ELSE,
            TokenType.FALSE.value: TokenType.FALSE,
            TokenType.DEFUN.value: TokenType.DEFUN,
            TokenType.FOR.value: TokenType.FOR,
            TokenType.IF.value: TokenType.IF,
            TokenType.NIL.value: TokenType.NIL,
            TokenType.OR.value: TokenType.OR,
            TokenType.PRINT.value: TokenType.PRINT,
            TokenType.RETURN.value: TokenType.RETURN,
            TokenType.SUPER.value: TokenType.SUPER,
            TokenType.THIS.value: TokenType.THIS,
            TokenType.TRUE.value: TokenType.TRUE,
            TokenType.VAR.value: TokenType.VAR,
            TokenType.WHILE.value: TokenType.WHILE,
        }
        token_type = keywords.get(value)
        if token_type is None:
            if value.startswith("'"):
                token_type = TokenType.SYMBOL
            else:
                token_type = TokenType.IDENTIFIER
        self._add_token(token_type)


if __name__ == '__main__':
    source = """\
    2000 - 200
"""
    scanner = Scanner(source=source)
    try:
        scanner.scan_tokens()
    except ScannerError:
        __import__('pprint').pprint(scanner.errors)
    else:
        __import__('pprint').pprint(scanner.tokens)
