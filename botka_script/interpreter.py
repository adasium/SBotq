from __future__ import annotations

from typing import List

import attr

from botka_script.tokens import TokenType


@attr.s(auto_attribs=True, kw_only=True)
class Visitor:
    pass


@attr.s(auto_attribs=True, kw_only=True)
class Interpreter(Visitor):
    errors: List[str] = attr.Factory(list)
    stdout: str = ''

    def interpret(self, expr: Expr):
        return self._evaluate(expr)

    def _evaluate(self, expr: Expr):
        return expr.accept(self)

    def visit_FunExpr(self, expr: DefunExpr):
        def divide(args):
            first, *rest = args
            for r in rest:
                first /= r
            return first

        def multiply(args):
            first, *rest = args
            for r in rest:
                first *= r
            return first

        def subtract(args):
            first, *rest = args
            for r in rest:
                first -= r
            return first


        _MISSING = object()

        builtin = {
            '+': sum,
            '-': subtract,
            '*': multiply,
            '/': divide,
            'message': None,
        }
        op = expr.op.lexeme
        fun = builtin.get(op, _MISSING)

        if fun is _MISSING:
            # TODO@adasium: custom functions
            raise NotImplementedError

        if fun is not None:
            return fun(
                self._evaluate(arg)
                for arg in expr.args
            )
        else:
            if op == 'message':
                for arg in expr.args:
                    self.stdout += str(self._evaluate(arg))
                return None
            assert False, 'unreachable'

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
