import pytest

from botka_script.expr import Expr
from botka_script.expr import Parser
from botka_script.interpreter import Interpreter
from botka_script.scanner import Scanner


def get_ast(source: str) -> Expr:
    scanner = Scanner(source=source)
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)
    expr = parser.parse()
    return expr


def test_two_plus_two():
    ast = get_ast(source='(+ 2 2)')
    interpreter = Interpreter()

    interpreter.interpret(ast)

    assert interpreter.stdout == ''


def test_message():
    ast = get_ast('(message "2 2")')
    interpreter = Interpreter()

    interpreter.interpret(ast)

    assert interpreter.stdout == '2 2'

@pytest.mark.parametrize(
    'op,result',
    [
        ('+', '6'),
        ('-', '-2'),
        ('*', '8'),
        ('/', '0.5'),
    ],
)
def test_message_expr(op, result):
    ast = get_ast(source=f'(message ({op} 2 2 2))')
    interpreter = Interpreter()

    interpreter.interpret(ast)

    assert interpreter.stdout == result
