from botka_script.scanner import Scanner
from botka_script.tokens import Token
from botka_script.tokens import TokenType


def test_empty():
    scanner = Scanner(source='')
    scanner.scan_tokens()
    assert scanner.tokens == [
        Token.from_type(
            type=TokenType.EOF,
            pos='0:0,0:0',
        ),
    ]
    assert scanner.errors == []


def test_addition():
    scanner = Scanner(source='2+2')
    scanner.scan_tokens()
    assert scanner.tokens == [
        Token.from_type(type=TokenType.INTEGER, lexeme='2',  literal=2,    pos='0:0'),
        Token.from_type(type=TokenType.SYMBOL,  lexeme='+2',               pos='0:1,0:2'),
        Token.from_type(type=TokenType.EOF,     lexeme='',   literal=None, pos='0:3'),
    ]
    assert scanner.errors == []


def test_symbol():
    scanner = Scanner(source='2+XD')
    scanner.scan_tokens()
    assert scanner.tokens == [
        Token.from_type(type=TokenType.INTEGER,    lexeme='2',   literal=2,    pos='0:0'),
        Token.from_type(type=TokenType.SYMBOL,     lexeme='+XD',               pos='0:1,0:3'),
        Token.from_type(type=TokenType.EOF,        lexeme='',    literal=None, pos='0:4'),
    ]
    assert scanner.errors == []
