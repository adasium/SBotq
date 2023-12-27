from typing import List

import attr

from botka_script.exceptions import ScannerError
from botka_script.tokens import Token
from botka_script.tokens import TokenType


@attr.s(auto_attribs=True, kw_only=True)
class Scanner:
    source: str
    tokens: List[Token] = attr.Factory(list)
    current: int = 0
    start: int = 0
    line: int = 1
    errors: List[str] = attr.Factory(list)

    def scan_tokens(self) -> None:

        while not self.is_at_end():
            self.start = self.current
            self._scan_token()

        self.tokens.append(
            Token(
                type=TokenType.EOF,
                lexeme='',
                literal=None,
                line=self.line,
            ),
        )

    def is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _scan_token(self) -> None:
        c = self._advance()
        one_char_tokens = {
            '(': TokenType.LEFT_PAREN,
            ')': TokenType.RIGHT_PAREN,
            '{': TokenType.LEFT_BRACE,
            '}': TokenType.RIGHT_BRACE,
            ',': TokenType.COMMA,
            '-': TokenType.MINUS,
            '+': TokenType.PLUS,
            ';': TokenType.SEMICOLON,
            '*': TokenType.ASTERISK,
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

        if c.isalpha():
            self._scan_identifier()
            return None

        self.errors.append(f'Unexpected character: `{c}`')
        raise ScannerError

    def _advance(self) -> str:
        c = self.source[self.current]
        self.current += 1
        return c

    def _add_token(self, token_type: TokenType, literal: object = None) -> None:
        text = self.source[self.start:self.current]
        self.tokens.append(
            Token(
                type=token_type,
                lexeme=text,
                literal=literal,
                line=self.line,
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

    def _scan_identifier(self) -> None:
        while self._peek().isalnum():
            self._advance()

        value = self.source[self.start:self.current]
        keywords = {
            'AND': TokenType.AND,
            'CLASS': TokenType.CLASS,
            'ELSE': TokenType.ELSE,
            'FALSE': TokenType.FALSE,
            'FUN': TokenType.FUN,
            'FOR': TokenType.FOR,
            'IF': TokenType.IF,
            'NIL': TokenType.NIL,
            'OR': TokenType.OR,
            'PRINT': TokenType.PRINT,
            'RETURN': TokenType.RETURN,
            'SUPER': TokenType.SUPER,
            'THIS': TokenType.THIS,
            'TRUE': TokenType.TRUE,
            'VAR': TokenType.VAR,
            'WHILE': TokenType.WHILE,
        }
        token_type = keywords.get(value, TokenType.IDENTIFIER)
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
