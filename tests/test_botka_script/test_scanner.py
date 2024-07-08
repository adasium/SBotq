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


def test_addition():
    scanner = Scanner(source='2+2')
    scanner.scan_tokens()
    assert scanner.tokens == [
        Token.from_type(type=TokenType.EOF, lexeme='2', literal=2, pos='0:0'),
        Token.from_type(type=TokenType.EOF, lexeme='+',            pos='0:1'),
        Token.from_type(type=TokenType.EOF, lexeme='2', literal=2, pos='0:2'),
        Token.from_type(type=TokenType.EOF, lexeme='', literal=None, pos='0:3'),
    ]
