from __future__ import annotations

import ast
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SQL_CALLS = {"text", "execute", "exec_driver_sql", "from_statement"}


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _is_dynamic_string(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    )


def test_application_sql_never_uses_interpolated_strings() -> None:
    """SQL values must be bound parameters, never formatted into SQL text."""
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) not in SQL_CALLS:
                continue
            if node.args and _is_dynamic_string(node.args[0]):
                relative = path.relative_to(APP_ROOT.parent)
                violations.append(f"{relative}:{node.lineno}")

    assert not violations, (
        "Dynamic SQL detected. Use SQLAlchemy expressions or text() with named "
        f"bind parameters instead: {', '.join(violations)}"
    )
