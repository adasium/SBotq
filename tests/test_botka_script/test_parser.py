import pytest

from botka_script.exceptions import ParseError
from botka_script.parser import AstPrinter
from botka_script.parser import DefunExpr
from botka_script.parser import FormExpr
from botka_script.parser import FunExpr
from botka_script.parser import IdentifierExpr
from botka_script.parser import LiteralExpr
from botka_script.parser import Parser
from botka_script.parser import SymbolExpr
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
    parser.parse()
    assert parser.errors == []


def test_two_plus_two():
    scanner = Scanner(source='(+ 2 2)')
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)

    expr = parser.parse()

    assert parser.errors == []
    assert expr == FormExpr(
        args=[
            FunExpr(
                op=Token.from_type(TokenType.IDENTIFIER, lexeme='+', pos='0:1'),
                args=[
                    LiteralExpr(value=2),
                    LiteralExpr(value=2),
                ],
            ),
        ],
    )


def test_message():
    scanner = Scanner(source='(message "2 2")')
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)

    expr = parser.parse()

    assert parser.errors == []
    assert expr == FormExpr(
        args=[
            FunExpr(
                op=Token.from_type(TokenType.IDENTIFIER, lexeme='message', pos='0:1,0:7'),
                args=[
                    LiteralExpr(value='2 2'),
                ],
            ),
        ],
    )


def test_call():
    source = '''\
(defun spoiler(text)
    (interactive "m")
    (message "||" text "||"))
(call \'spoiler)
    '''
    scanner = Scanner(source=source)
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)

    expr = parser.parse()

    assert parser.errors == []
    expected = FormExpr(
        args=[
            DefunExpr(
                op=Token.from_type(TokenType.IDENTIFIER, lexeme='spoiler', pos='0:7,0:13'),
                args=[
                    IdentifierExpr(op=Token.from_type(TokenType.IDENTIFIER, lexeme='text', pos='0:15,0:18')),
                ],
                form=FormExpr(
                    args=[
                        FunExpr(
                            op=Token.from_type(TokenType.IDENTIFIER, lexeme='interactive', pos='1:6,1:16'),
                            args=['m'],
                        ),
                        FunExpr(
                            op=Token.from_type(TokenType.IDENTIFIER, lexeme='message', pos='2:6,2:12'),
                            args=[
                                LiteralExpr(value='||'),
                                IdentifierExpr(op=Token.from_type(TokenType.IDENTIFIER, lexeme='text')),
                            ],
                        ),
                    ],
                ),
            ),
            FunExpr(
                op=Token.from_type(TokenType.IDENTIFIER, lexeme='call', pos='3:2,3:5'),
                args=[
                    SymbolExpr(op=Token.from_type(TokenType.SYMBOL, lexeme='spoiler')),
                ],
            ),
        ],
    )
    assert AstPrinter().print(expr) == AstPrinter().print(expected)
    # assert expr == expected, __import__('pprint').pprint((
    #     AstPrinter().print(expr),
    #     AstPrinter().print(expected)
    # ))


def test_call_on_response():
    source = '''\
(defun spoiler(text)
    (interactive "r")
    (message "||" text "||"))
(call \'spoiler)
    '''
    scanner = Scanner(source=source)
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)

    expr = parser.parse()

    assert parser.errors == []
    expected = FormExpr(
        args=[
            DefunExpr(
                op=Token.from_type(TokenType.IDENTIFIER, lexeme='spoiler', pos='0:7,0:13'),
                args=[
                    IdentifierExpr(op=Token.from_type(TokenType.IDENTIFIER, lexeme='text', pos='0:15,0:18')),
                ],
                form=FormExpr(
                    args=[
                        FunExpr(
                            op=Token.from_type(TokenType.IDENTIFIER, lexeme='interactive', pos='1:6,1:16'),
                            args=['m'],
                        ),
                        FunExpr(
                            op=Token.from_type(TokenType.IDENTIFIER, lexeme='message', pos='2:6,2:12'),
                            args=[
                                LiteralExpr(value='||'),
                                IdentifierExpr(op=Token.from_type(TokenType.IDENTIFIER, lexeme='text')),
                            ],
                        ),
                    ],
                ),
            ),
            FunExpr(
                op=Token.from_type(TokenType.IDENTIFIER, lexeme='call', pos='3:2,3:5'),
                args=[
                    SymbolExpr(op=Token.from_type(TokenType.SYMBOL, lexeme='spoiler')),
                ],
            ),
        ],
    )
    assert AstPrinter().print(expr) == AstPrinter().print(expected)
    # assert expr == expected, __import__('pprint').pprint((
    #     AstPrinter().print(expr),
    #     AstPrinter().print(expected)
    # ))
