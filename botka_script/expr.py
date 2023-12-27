from __future__ import annotations

from typing import List

import attr

from botka_script.scanner import Scanner
from botka_script.tokens import Token
from botka_script.tokens import TokenType


class ParseError(Exception):
    pass



@attr.s(auto_attribs=True, kw_only=True)
class Expr:
    def accept(self, visitor: Visitor):
        return getattr(visitor, f'visit_{self.__class__.__name__}')(self)


@attr.s(auto_attribs=True, kw_only=True)
class BinaryExpr(Expr):
    left: Expr
    op: Token
    right: Expr


@attr.s(auto_attribs=True, kw_only=True)
class GroupingExpr(Expr):
    expr: Expr


@attr.s(auto_attribs=True, kw_only=True)
class LiteralExpr(Expr):
    value: object


@attr.s(auto_attribs=True, kw_only=True)
class UnaryExpr(Expr):
    op: Token
    right: Expr


@attr.s(auto_attribs=True, kw_only=True)
class Visitor:
    pass


@attr.s(auto_attribs=True, kw_only=True)
class AstPrinter(Visitor):
    def print(self, expr: Expr):
        return expr.accept(self)

    def visit_BinaryExpr(self, expr: BinaryExpr):
        return self.parenthesize(expr.op.lexeme, expr.left, expr.right)

    def visit_GroupingExpr(self, expr: GroupingExpr):
        return self.parenthesize('group', expr.expr)

    def visit_LiteralExpr(self, expr: LiteralExpr):
        if expr.value is None:
            return 'nil'
        else:
            return str(expr.value)

    def visit_UnaryExpr(self, expr: UnaryExpr):
        return self.parenthesize(expr.op.lexeme, expr.right)

    def parenthesize(self, name: str, *exprs: Expr):
        exprs_str = ''
        if exprs:
            exprs_str += ' '.join(expr.accept(self) for expr in exprs)
            return f'({name} {exprs_str})'
        else:
            return f'({name})'


@attr.s(auto_attribs=True, kw_only=True)
class Interpreter(Visitor):
    errors: List[str] = attr.Factory(list)

    def interpret(self, expr: Expr):
        return self._evaluate(expr)

    def _evaluate(self, expr: Expr):
        return expr.accept(self)

    def visit_BinaryExpr(self, expr: BinaryExpr):
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)
        if expr.op.type == TokenType.MINUS:
            return left - right
        if expr.op.type == TokenType.SLASH:
            return left / right
        if expr.op.type == TokenType.ASTERISK:
            return left * right
        if expr.op.type == TokenType.PLUS:
            return left + right

        if expr.op.type == TokenType.GREATER:
            return left > right
        if expr.op.type == TokenType.GREATER_EQUAL:
            return left >= right
        if expr.op.type == TokenType.LESS:
            return left < right
        if expr.op.type == TokenType.LESS_EQUAL:
            return left <= right

        if expr.op.type == TokenType.BANG_EQUAL:
            return not self._is_equal(left, right)
        if expr.op.type == TokenType.EQUAL_EQUAL:
            return self._is_equal(left, right)

        assert False, 'unreachable'

    def _is_equal(self, left: object, right: object) -> bool:
        return left == right

    def visit_GroupingExpr(self, expr: GroupingExpr) -> object:
        return self._evaluate(expr.expr)

    def visit_LiteralExpr(self, expr: LiteralExpr) -> object:
        return expr.value

    def visit_UnaryExpr(self, expr: UnaryExpr) -> object:
        right = self._evaluate(expr.right)
        if expr.op.type == TokenType.MINUS:
            return -right
        if expr.op.type == TokenType.BANG:
            return self._is_truthy(right)
        assert False, 'unreachable'

    def _is_truthy(self, obj: object) -> bool:
        if obj is None:
            return False
        if isinstance(obj, bool):
            return bool(obj)
        return True

    def parenthesize(self, name: str, *exprs: Expr):
        exprs_str = ''
        if exprs:
            exprs_str += ' '.join(expr.accept(self) for expr in exprs)
            return f'({name} {exprs_str})'
        else:
            return f'({name})'



@attr.s(auto_attribs=True, kw_only=True)
class Parser:
    tokens: List[Token]
    current: int = 0
    errors: List[str] = attr.Factory(list)

    def _expression(self):
        return self._equality()

    def _equality(self):
        expr = self._comparison()
        while self._match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expr = BinaryExpr(left=expr, op=operator, right=right)
        return expr

    def _match(self, *token_types: TokenType) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _comparison(self) -> Expr:
        expr = self._term()
        _tokens = [
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
        ]
        while self._match(*_tokens):
            operator = self._previous()
            right = self._term()
            expr = BinaryExpr(left=expr, op=operator, right=right)
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._match(TokenType.MINUS, TokenType.PLUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryExpr(left=expr, op=operator, right=right)
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._match(TokenType.SLASH, TokenType.ASTERISK):
            operator = self._previous()
            right = self._unary()
            expr = BinaryExpr(left=expr, op=operator, right=right)
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            operator = self._previous()
            right = self._unary()
            return UnaryExpr(op=operator, right=right)
        return self._primary()

    def _primary(self) -> Expr:
        if self._match(TokenType.FALSE):
            return LiteralExpr(value=False)

        if self._match(TokenType.TRUE):
            return LiteralExpr(value=True)

        if self._match(TokenType.NIL):
            return LiteralExpr(value=None)

        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(value=self._previous().literal)

        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, 'expected `)` after expression.')
            return GroupingExpr(expr=expr)
        raise self._error(self._peek(), 'expected expression')

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()

        raise self._error(self._peek(), message)

    def _error(self, token: Token, message: str) -> ParseError:
        error = f'error at token={token}, {message}'
        self.errors.append(error)
        return ParseError()

    def _synchronize(self) -> None:
        self._advance()
        while not self._is_at_end():
            if self._previous().type == TokenType.SEMICOLON:
                return
            if self._peek().type in [
                TokenType.CLASS,
                TokenType.FUN,
                TokenType.VAR,
                TokenType.FOR,
                TokenType.IF,
                TokenType.WHILE,
                TokenType.PRINT,
                TokenType.RETURN,
            ]:
                self._advance()

    def parse(self) -> Expr:
        return self._expression()


def interpret(source: str) -> str:
    scanner = Scanner(source=source)
    try:
        scanner.scan_tokens()
    except Exception:
        if not scanner.errors:
            _errors = 'tudu'
        else:
            _errors = str(scanner.errors)
        return f'Scanner exception: {_errors}'

    parser = Parser(tokens=scanner.tokens)
    try:
        expr = parser.parse()
    except Exception:
        if not parser.errors:
            _errors = 'tudu'
        else:
            _errors = str(parser.errors)
        return f'Parser exception: {_errors}'

    interpreter = Interpreter()
    try:
        return str(interpreter.interpret(expr))
    except Exception as e:
        if not interpreter.errors:
            _errors = 'tudu'
        else:
            _errors = str(interpreter.errors)
        return f'Interpreter exception: {_errors}'


if __name__ == '__main__':
    source = """\
    2+2
"""
    scanner = Scanner(source=source)
    try:
        scanner.scan_tokens()
    except NotImplementedError:
        __import__('pprint').pprint(scanner.errors)
    else:
        __import__('pprint').pprint(scanner.tokens)
        parser = Parser(tokens=scanner.tokens)
        try:
            expr = parser.parse()
        except ParseError:
            __import__('pprint').pprint(parser.errors)
        else:
            __import__('pprint').pprint(AstPrinter().print(expr))
            __import__('pprint').pprint(Interpreter().interpret(expr))
