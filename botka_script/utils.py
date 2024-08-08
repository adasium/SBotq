import attr

from botka_script.interpreter import Interpreter
from botka_script.parser import Parser
from botka_script.scanner import Scanner


@attr.s(auto_attribs=True, kw_only=True)
class InterpreterResult:
    success: bool
    stdout: str = ''
    stderr: str = ''
    e: Exception | None = None


def interpret_source(source: str, exc: Exception = ValueError, **kwargs) -> InterpreterResult:
    scanner = Scanner(source=source)
    try:
        scanner.scan_tokens()
    except exc as e:
        return InterpreterResult(
            success=False,
            stderr=f'Scanner exception: {scanner.errors}',
            e=e,
        )

    parser = Parser(tokens=scanner.tokens)
    try:
        expr = parser.parse()
    except exc:
        return InterpreterResult(
            success=False,
            stderr=f'Parser exception: {parser.errors}',
            e=e,
        )

    interpreter = Interpreter(extra=kwargs)
    try:
        final_expr = interpreter.interpret(expr)
    except exc as e:
        return InterpreterResult(
            success=False,
            stderr=f'Interpreter exception: {e}',
            e=e,
        )
    else:
        return InterpreterResult(
            success=True,
            stdout=str(interpreter.stdout or (final_expr is not None and final_expr) or ''),
            e=None,
        )
