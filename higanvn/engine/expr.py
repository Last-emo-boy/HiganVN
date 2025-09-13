from __future__ import annotations

import ast
from typing import Any, Dict


class SafeEval(ast.NodeVisitor):
    """Tiny safe expression evaluator for SET/IF.

    Supported:
    - Literals: int/float/str/bool/None
    - Names: from vars dict (missing -> None)
    - Unary: +x, -x, not x
    - Binary: + - * / // %
    - Bool ops: and/or
    - Comparisons: == != < <= > >=, chainable
    - Parentheses (via AST structure)
    """

    def __init__(self, vars: Dict[str, Any]):
        self.vars = vars

    def evaluate(self, expr: str) -> Any:
        # Normalize smart quotes to standard for strings
        expr = (
            expr.replace('“', '"').replace('”', '"')
            .replace('「', '"').replace('」', '"')
        )
        tree = ast.parse(expr, mode="eval")
        return self.visit(tree.body)

    def visit_Constant(self, node: ast.Constant) -> Any:  # py>=3.8
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        key = node.id
        # common lowercase aliases
        if key.lower() == 'true':
            return True
        if key.lower() == 'false':
            return False
        if key.lower() == 'none':
            return None
        return self.vars.get(key, None)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        v = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.Not):
            return not v
        raise ValueError("Unsupported unary operator")

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            result = True
            for v in node.values:
                result = result and bool(self.visit(v))
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for v in node.values:
                result = result or bool(self.visit(v))
            return result
        raise ValueError("Unsupported boolean operator")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        l = self.visit(node.left)
        r = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return l + r
        if isinstance(node.op, ast.Sub):
            return l - r
        if isinstance(node.op, ast.Mult):
            return l * r
        if isinstance(node.op, ast.Div):
            return l / r
        if isinstance(node.op, ast.FloorDiv):
            return l // r
        if isinstance(node.op, ast.Mod):
            return l % r
        raise ValueError("Unsupported binary operator")

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        result = True
        cur_left = left
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            ok = False
            if isinstance(op, ast.Eq):
                ok = cur_left == right
            elif isinstance(op, ast.NotEq):
                ok = cur_left != right
            elif isinstance(op, ast.Lt):
                ok = cur_left < right
            elif isinstance(op, ast.LtE):
                ok = cur_left <= right
            elif isinstance(op, ast.Gt):
                ok = cur_left > right
            elif isinstance(op, ast.GtE):
                ok = cur_left >= right
            else:
                raise ValueError("Unsupported comparison")
            result = result and ok
            cur_left = right
        return result

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def safe_eval(expr: str, vars: Dict[str, Any]) -> Any:
    return SafeEval(vars).evaluate(expr)
