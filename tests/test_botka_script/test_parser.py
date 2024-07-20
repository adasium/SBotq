import pytest

from botka_script.exceptions import ParseError
from botka_script.expr import FunExpr
from botka_script.expr import LiteralExpr
from botka_script.expr import Parser
from botka_script.scanner import Scanner
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
    scanner = Scanner(source='(+ 2 2)')
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)

    expr = parser.parse()

    assert parser.errors == []
    assert expr == FunExpr(
        op=Token.from_type(TokenType.SYMBOL, lexeme='+', pos='0:1'),
        args=[
            LiteralExpr(value=2),
            LiteralExpr(value=2),
        ],
    )


def test_message():
    scanner = Scanner(source='(message "2 2")')
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)

    expr = parser.parse()

    assert parser.errors == []
    assert expr == FunExpr(
        op=Token.from_type(TokenType.SYMBOL, lexeme='message', pos='0:1,0:7'),
        args=[
            LiteralExpr(value='2 2'),
        ],
    )
