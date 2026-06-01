import ast
import operator
import re
from typing import Any

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_safe_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    raise ValueError("Biểu thức không hợp lệ hoặc chứa phép toán không được phép")


def sanitize_expression(expr: str) -> str:
    """Strip dangerous chars; keep digits, operators, parentheses, spaces, dots."""
    cleaned = re.sub(r"[^0-9+\-*/().%\s]", "", expr)
    return cleaned.strip()


def calculate(expression: str) -> dict[str, Any]:
    cleaned = sanitize_expression(expression)
    if not cleaned:
        return {"ok": False, "error": "Biểu thức rỗng sau khi lọc."}
    try:
        tree = ast.parse(cleaned, mode="eval")
        value = _safe_eval_node(tree)
        return {
            "ok": True,
            "expression": cleaned,
            "result": value,
            "formatted_vnd": f"{int(value):,} VNĐ".replace(",", ".") if value >= 1_000_000 else f"{value:,.0f}",
        }
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
        return {"ok": False, "error": str(e), "expression": cleaned}


def price_difference(price_a: float, price_b: float) -> dict[str, Any]:
    diff = price_a - price_b
    return {
        "ok": True,
        "price_a": price_a,
        "price_b": price_b,
        "difference": diff,
        "cheaper": "a" if diff > 0 else ("b" if diff < 0 else "equal"),
        "formatted_difference_vnd": f"{int(abs(diff)):,} VNĐ".replace(",", "."),
    }


def down_payment(price: float, percent: float) -> dict[str, Any]:
    if not 0 < percent <= 100:
        return {"ok": False, "error": "Phần trăm phải trong khoảng (0, 100]."}
    amount = price * (percent / 100.0)
    return {
        "ok": True,
        "price": price,
        "percent": percent,
        "down_payment": amount,
        "formatted_vnd": f"{int(amount):,} VNĐ".replace(",", "."),
    }
