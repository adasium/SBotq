from __future__ import annotations

from typing import List

import attr

from botka_script.exceptions import InterpreterError
from botka_script.parser import DefunExpr
from botka_script.parser import FormExpr
from botka_script.parser import FunExpr
from botka_script.parser import IdentifierExpr
from botka_script.parser import SymbolExpr
from botka_script.tokens import TokenType

_MISSING = object()

@attr.s(auto_attribs=True, kw_only=True)
class Visitor:
    pass


@attr.s(auto_attribs=True, kw_only=True)
class Interpreter(Visitor):
    errors: List[str] = attr.Factory(list)
    stdout: str = ''
    extra: dict = attr.Factory(dict)
    identifiers: dict = attr.Factory(dict)
    stack: list = attr.Factory(list)

    def interpret(self, expr: Expr):
        return self._evaluate(expr)

    def _evaluate(self, expr: Expr):
        return expr.accept(self)

    def visit_FormExpr(self, expr: FormExpr):
        for arg in expr.args:
            arg.accept(self)

    def visit_FunExpr(self, expr: FunExpr):
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

        builtin = {
            '+': sum,
            '-': subtract,
            '*': multiply,
            '/': divide,
            'message': None,
            'call': None,
            'interactive': None,
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
            if op == 'interactive':
                if len(expr.args) == 0:
                    expr.args == 'm'
                for arg in expr.args:
                    for char in arg.value:
                        if char == 'm':
                            try:
                                self.stack[-1]['_m'] = self.extra['current_message_context']
                            except KeyError:
                                self.errors.append('not called in Discord context.')
                        if char == 'r':
                            try:
                                self.stack[-1]['_m'] = self.extra['referenced_message']
                            except KeyError:
                                self.errors.append('not called in Discord context.')
                return None
            if op == 'message':
                for arg in expr.args:
                    self.stdout += str(self._evaluate(arg))
                return None

            if op == 'call':
                first, *rest = expr.args
                if isinstance(first, SymbolExpr):
                    function_to_call = self.identifiers[first.op.lexeme.lstrip("'")]
                else:
                    raise NotImplementedError(first)

                if not isinstance(function_to_call, DefunExpr):
                    raise InterpreterError(f'{first} is not callable')
                else:
                    return self._call_function(
                        function_to_call,
                        args=[
                            self._evaluate(r)
                            for r in rest
                        ],
                    )
            assert False, 'unreachable'

    def _call_function(self, expr: DefunExpr, args: list[Expr]):
        self.stack.append({})
        # self.stack.append({
        #     arg.op.lexeme: self._evaluate(arg)
        #     for arg in expr.args
        # })
        result = None
        first, *rest = expr.form.args or [None]

        if len(args) != len(expr.form.args):
            if first is not None and first.op.lexeme == 'interactive':
                interactive_args = expr.form.args[0].args
                if len(interactive_args) == 0:
                    self.stack[-1][expr.args[0].op.lexeme] = self.extra['current_message_context']
                elif interactive_args[0].value == 'm':
                    self.stack[-1][expr.args[0].op.lexeme] = self.extra['current_message_context']
                    rest = expr.form.args
                elif interactive_args[0].value == 'r':
                    if 'referenced_message' not in self.extra:
                        raise InterpreterError('(interactive "r") was specified but no referenced message found')
                    self.stack[-1][expr.args[0].op.lexeme] = self.extra['referenced_message']
                    rest = expr.form.args
            else:
                raise InterpreterError(f'param count is off (got {len(args)}, expected {len(expr.form.args)})')
        else:
            for arg, param in zip(args, expr.form.args):
                self.stack[-1][param.op.lexeme] = arg

        for expr in rest:
            result = self._evaluate(expr)
        return result

    def visit_DefunExpr(self, expr: DefunExpr):
        self.identifiers[expr.op.lexeme] = expr
        return None

    def visit_IdentifierExpr(self, expr: IdentifierExpr):
        val = self.stack[-1].get(expr.op.lexeme, _MISSING)
        if val is _MISSING:
            return self.identifiers[expr.op.lexeme]
        else:
            return val

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
