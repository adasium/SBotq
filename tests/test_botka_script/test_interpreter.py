import pytest

from botka_script.exceptions import InterpreterError
from botka_script.interpreter import Interpreter
from botka_script.parser import Expr
from botka_script.parser import Parser
from botka_script.scanner import Scanner
from botka_script.utils import interpret_source


def get_ast(source: str) -> Expr:
    scanner = Scanner(source=source)
    scanner.scan_tokens()
    parser = Parser(tokens=scanner.tokens)
    expr = parser.parse()
    return expr


def test_two_plus_two():
    result = interpret_source('(+ 2 2 2)')
    assert result.stdout == '6'
    assert result.success


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


def test_defun():
    discord_message = 'this_is_text'
    source = '''\
    (defun spoiler(text)
        (interactive)
        (message "||" text "||"))
    (call \'spoiler)
    '''
    result = interpret_source(source, current_message_context=discord_message)
    assert result.e is None, result.e

    assert result.stdout == f'||{discord_message}||'


def test_defun_referenced_message():
    current_message_context = 'this_is_text'
    referenced_message = 'this_is_other_text'
    source = '''\
    (defun spoiler(text)
        (interactive "r")
        (message "||" text "||"))
    (call \'spoiler)
    '''
    result = interpret_source(source, current_message_context=current_message_context, referenced_message=referenced_message)
    assert result.e is None, result.e

    assert result.stdout == f'||{referenced_message}||'


def test_defun_no_referenced_message():
    current_message_context = 'this_is_text'
    source = '''\
    (defun spoiler(text)
        (interactive "r")
        (message "||" text "||"))
    (call \'spoiler)
    '''
    result = interpret_source(source, current_message_context=current_message_context, exc=InterpreterError)
    assert not result.success
    assert isinstance(result.e, InterpreterError), result.e
    assert result.stderr == 'Interpreter exception: (interactive "r") was specified but no referenced message found'
