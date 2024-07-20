import attr

from botka_script.expr import Parser
from botka_script.interpreter import Interpreter
from botka_script.scanner import Scanner


@attr.s(auto_attribs=True, kw_only=True)
class InterpreterResult:
    success: bool
    stdout: str = ''
    stderr: str = ''


def interpret_source(source: str) -> InterpreterResult:
    scanner = Scanner(source=source)
    try:
        scanner.scan_tokens()
    except Exception:
        return InterpreterResult(
            success=False,
            stderr=f'Scanner exception: {scanner.errors}',
        )

    parser = Parser(tokens=scanner.tokens)
    try:
        expr = parser.parse()
    except Exception:
        return InterpreterResult(
            success=False,
            stderr=f'Parser exception: {parser.errors}',
        )

    interpreter = Interpreter()
    try:
        final_expr = interpreter.interpret(expr)
    except Exception as e:
        return InterpreterResult(
            success=False,
            stderr=f'Interpreter exception: {interpreter.errors}',
        )
    else:
        return InterpreterResult(
            success=True,
            stdout=str(interpreter.stdout or final_expr),
        )
