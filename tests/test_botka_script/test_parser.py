import pytest

from botka_script.exceptions import ParseError
from botka_script.expr import BinaryExpr
from botka_script.expr import LiteralExpr
from botka_script.expr import Parser
from botka_script.tokens import Token
from botka_script.tokens import TokenType


def test_empty():
    parser = Parser(
        tokens=[],
    )
    with pytest.raises(ParseError) as excinfo:
        parser.parse()
    assert parser.errors == ['expected at least one token']


def test_eof():
    token = Token.from_type(type=TokenType.EOF)
    parser = Parser(tokens=[token])
    with pytest.raises(ParseError):
        parser.parse()
        assert parser.errors == [
            f'error at token={token}, expected expression',
        ]


def test_two_plus_two():
    tokens = [
        Token.from_type(type=TokenType.INTEGER, lexeme='2', literal=2,    pos='0:0'),
        Token.from_type(type=TokenType.PLUS,    lexeme='+',               pos='0:1'),
        Token.from_type(type=TokenType.INTEGER, lexeme='2', literal=2,    pos='0:2'),
        Token.from_type(type=TokenType.EOF,     lexeme='',  literal=None, pos='0:3'),
    ]
    parser = Parser(tokens=tokens)
    expr = parser.parse()
    assert parser.errors == []
    assert expr == BinaryExpr(
        left=LiteralExpr(value=2),
        op=tokens[1],
        right=LiteralExpr(value=2),
    )
