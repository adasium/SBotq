from __future__ import annotations

import re
from enum import Enum

import attr

class TokenType(Enum):

    LEFT_PAREN = '('
    RIGHT_PAREN = ')'
    LEFT_BRACE = '{'
    RIGHT_BRACE = '}'
    COMMA = ','
    DOT = '.'
    MINUS = '-'
    PLUS = '+'
    SEMICOLON = ';'
    SLASH = '/'
    ASTERISK = '*'

    # One or two character tokens.
    BANG = '!'
    BANG_EQUAL = '!='
    EQUAL = '='
    EQUAL_EQUAL = '=='
    GREATER = '>'
    GREATER_EQUAL = '>='
    LESS = '<'
    LESS_EQUAL = '<='

    # Literals.
    IDENTIFIER = 'IDENTIFIER'
    STRING = 'STRING'
    NUMBER = 'NUMBER'
    INTEGER = 'INTEGER'

    # Keywords.
    AND = 'AND'
    CLASS = 'CLASS'
    ELSE = 'ELSE'
    FALSE = 'FALSE'
    FUN = 'FUN'
    FOR = 'FOR'
    IF = 'IF'
    NIL = 'NIL'
    OR = 'OR'
    PRINT = 'PRINT'
    RETURN = 'RETURN'
    SUPER = 'SUPER'
    THIS = 'THIS'
    TRUE = 'TRUE'
    VAR = 'VAR'
    WHILE = 'WHILE'

    EOF = 'EOF'


@attr.s(auto_attribs=True, kw_only=True)
class Token:
    type: TokenType
    lexeme: str
    literal: object
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    @classmethod
    def from_type(
        cls,
        type: TokenType,
        pos: str | None = None,
        start_line: int | None = None,
        start_column: int | None = None,
        end_line: int | None = None,
        end_column: int | None = None,
        lexeme: str = None,
        literal: object = None,
    ) -> Token:
        if end_line is None:
            end_line = start_line
        if end_column is None:
            end_column = start_column
        if pos is not None:
            parts = list(map(str.strip, pos.split(',')))
            if len(parts) == 1:
                line, column = list(map(int, map(str.strip, parts[0].split(':'))))
                start_line = end_line = line
                start_column = end_column = column
            else:
                start_line, start_column, end_line, end_column = list(map(int, map(str.strip, re.split('[,:]', pos))))
        return cls(
            type=TokenType.EOF,
            lexeme=lexeme or '',
            literal=None,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line or start_line,
            end_column=end_column or start_column,
        )
