from __future__ import annotations

import ast
from typing import Any, Dict, Set


# Whitelisted builtins for expressions/statements
_ALLOWED_BUILTINS: Dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "int": int,
    "float": float,
    "str": str,
    "len": len,
    "range": range,
    "round": round,
    "bool": bool,
}

# Allowed AST node types for a tiny safe subset of Python
_ALLOWED_NODES: Set[type] = {
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AugAssign,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.If,
    ast.While,
    ast.For,
    ast.Call,
    ast.arguments,
    ast.IfExp,
    ast.Pass,
    ast.Break,
    ast.Continue,
    # operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UAdd, ast.USub,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
}

# Only allow Call to whitelisted names (builtins) and range

def _validate_node(node: ast.AST) -> None:
    if type(node) not in _ALLOWED_NODES:
        raise ValueError(f"Disallowed node: {type(node).__name__}")
    # No attribute access, subscripting, lambda/def, import, with, etc.
    if isinstance(node, (ast.Attribute, ast.Subscript, ast.Import, ast.ImportFrom, ast.With, ast.Lambda, ast.FunctionDef, ast.ClassDef, ast.Try)):
        raise ValueError(f"Disallowed construct: {type(node).__name__}")
    # Calls must be to allowed builtin names
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_BUILTINS:
            raise ValueError("Only simple calls to allowed builtins are permitted")
    for child in ast.iter_child_nodes(node):
        _validate_node(child)


def safe_exec(code: str, vars: Dict[str, Any]) -> None:
    """Execute a tiny, safe subset of Python statements on the provided vars dict.

    Allowed:
    - Assignments: x = 1, x += 2
    - If/While with simple numeric/boolean expressions
    - For loops over range(...)
    - Expressions and calls to a small builtin whitelist: abs, min, max, int, float, str, len, range, round, bool

    Side effects are limited to updating the provided vars dict.
    """
    # Normalize line endings and strip BOM if any
    code_str = str(code or "").replace("\r\n", "\n").replace("\r", "\n")
    # Parse and validate AST
    tree = ast.parse(code_str, mode="exec")
    _validate_node(tree)
    # Exec with limited builtins and the vars mapping as locals
    exec(compile(tree, filename="<script>", mode="exec"), {"__builtins__": _ALLOWED_BUILTINS}, vars)
