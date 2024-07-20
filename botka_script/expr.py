from __future__ import annotations

from typing import List

import attr

from botka_script.exceptions import ParseError
from botka_script.tokens import Token
from botka_script.tokens import TokenType


@attr.s(auto_attribs=True, kw_only=True)
class Expr:
    def accept(self, visitor: Visitor):
        return getattr(visitor, f'visit_{self.__class__.__name__}')(self)


@attr.s(auto_attribs=True, kw_only=True)
class DefunExpr(Expr):
    op: Token
    args: list[Expr]


@attr.s(auto_attribs=True, kw_only=True)
class FunExpr(Expr):
    op: Token
    args: list[Expr]


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
class Parser:
    tokens: List[Token]
    current: int = 0
    errors: List[str] = attr.Factory(list)

    def _expression(self):
        return self._fun()
        # return self._equality()

    def _defun(self) -> Expr:
        self._match(TokenType.LEFT_PAREN)
        self._match(TokenType.FUN)
        self._match(TokenType.SYMBOL)
        self._match(TokenType.LEFT_PAREN)
        # TODO@adasium: args
        self._match(TokenType.RIGHT_PAREN)
        self._match(TokenType.RIGHT_PAREN)

    def _fun(self) -> Expr:
        self._match(TokenType.LEFT_PAREN)
        self._match(TokenType.SYMBOL)
        symbol = self._previous()
        args = self._fun_args()
        self._match(TokenType.RIGHT_PAREN)
        return FunExpr(
            op=symbol,
            args=args,
        )

    def _fun_args(self) -> list[Expr]:
        args = []
        while not self._check(TokenType.RIGHT_PAREN):
            arg = self._primary()
            args.append(arg)
        return args

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

        if self._match(TokenType.NUMBER, TokenType.INTEGER, TokenType.STRING):
            return LiteralExpr(value=self._previous().literal)

        if self._check(TokenType.LEFT_PAREN):
            return self._expression()
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
        if len(self.tokens) < 1:
            self.errors.append('expected at least one token')
            raise ParseError()
        return self._expression()
