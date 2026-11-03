from __future__ import annotations

import ast
from dataclasses import dataclass
import math
import re
from typing import Any, Mapping

import numpy as np


class MathExpressionError(ValueError):
    pass


_ALLOWED_FUNCTIONS = {
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "asin": np.arcsin,
    "acos": np.arccos,
    "atan": np.arctan,
    "atan2": np.arctan2,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,
    "exp": np.exp,
    "log": np.log,
    "ln": np.log,
    "log10": np.log10,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "floor": np.floor,
    "ceil": np.ceil,
}
_ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}
_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)
_SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_FUNCTION_DEF = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\(([^()]*)\)\s*=\s*(.+)$")


def normalize_math_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("equation must be text")
    value = text.strip()
    if not value:
        raise MathExpressionError("equation must be non-empty")
    if len(value) > 4096:
        raise MathExpressionError("equation exceeds 4096-character safety limit")
    replacements = {
        "−": "-",
        "–": "-",
        "×": "*",
        "·": "*",
        "÷": "/",
        "π": "pi",
        "α": "alpha",
        "β": "beta",
        "γ": "gamma",
        "δ": "delta",
        "θ": "theta",
        "λ": "lambda_",
        "μ": "mu",
        "σ": "sigma",
        "φ": "phi",
        "ω": "omega",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(r"√\s*\(", "sqrt(", value)
    value = value.replace("^", "**")
    value = re.sub(r"\bln\s*\(", "log(", value)

    # Friendly implicit multiplication for common handwritten forms such as
    # 2x, 3pi, 2(x+1), and )( . Keep this deliberately conservative so function
    # calls remain unambiguous and scientific semantics are never guessed.
    value = re.sub(r"(?<=\d)(?=[A-Za-z(])", "*", value)
    value = re.sub(r"(?<=\))(?=[A-Za-z0-9(])", "*", value)
    return value


def _validate_tree(tree: ast.AST) -> None:
    nodes = list(ast.walk(tree))
    if len(nodes) > 512:
        raise MathExpressionError("expression exceeds 512-node safety limit")
    for node in nodes:
        if isinstance(node, ast.Expression | ast.Load):
            continue
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise MathExpressionError("only real numeric constants are allowed")
            number = float(node.value)
            if not math.isfinite(number):
                raise MathExpressionError("numeric constants must be finite")
            if abs(number) > 1e308:
                raise MathExpressionError("numeric constant magnitude is too large")
            continue
        if isinstance(node, ast.Name):
            if not _SAFE_NAME.fullmatch(node.id):
                raise MathExpressionError(f"invalid identifier: {node.id!r}")
            continue
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, _ALLOWED_BINOPS):
                raise MathExpressionError("unsupported binary operator")
            continue
        if isinstance(node, _ALLOWED_BINOPS):
            continue
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, _ALLOWED_UNARYOPS):
                raise MathExpressionError("unsupported unary operator")
            continue
        if isinstance(node, _ALLOWED_UNARYOPS):
            continue
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise MathExpressionError("only direct named math functions are allowed")
            if node.func.id not in _ALLOWED_FUNCTIONS:
                raise MathExpressionError(f"unsupported function: {node.func.id}")
            if node.keywords:
                raise MathExpressionError("keyword function arguments are not supported")
            if len(node.args) > 4:
                raise MathExpressionError("math function call has too many arguments")
            continue
        raise MathExpressionError(
            f"unsupported expression syntax: {type(node).__name__}"
        )


def _parse_expression(text: str) -> ast.Expression:
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise MathExpressionError(f"invalid mathematical expression: {exc.msg}") from exc
    _validate_tree(tree)
    return tree


def _canonical(tree: ast.Expression) -> str:
    return ast.unparse(tree.body)

def _latex_node(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Name):
        greek = {
            "pi": r"\pi",
            "tau": r"\tau",
            "alpha": r"\alpha",
            "beta": r"\beta",
            "gamma": r"\gamma",
            "delta": r"\delta",
            "theta": r"\theta",
            "lambda_": r"\lambda",
            "mu": r"\mu",
            "sigma": r"\sigma",
            "phi": r"\phi",
            "omega": r"\omega",
        }
        return greek.get(node.id, node.id)
    if isinstance(node, ast.UnaryOp):
        value = _latex_node(node.operand)
        if isinstance(node.op, ast.USub):
            return "-" + value
        return "+" + value
    if isinstance(node, ast.BinOp):
        left = _latex_node(node.left)
        right = _latex_node(node.right)
        if isinstance(node.op, ast.Add):
            return rf"\left({left}+{right}\right)"
        if isinstance(node.op, ast.Sub):
            return rf"\left({left}-{right}\right)"
        if isinstance(node.op, ast.Mult):
            return rf"\left({left}\,{right}\right)"
        if isinstance(node.op, ast.Div):
            return rf"\frac{{{left}}}{{{right}}}"
        if isinstance(node.op, ast.Pow):
            return rf"{{{left}}}^{{{right}}}"
        if isinstance(node.op, ast.Mod):
            return rf"\operatorname{{mod}}\left({left},{right}\right)"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        args = [_latex_node(arg) for arg in node.args]
        name = node.func.id
        if name == "sqrt" and len(args) == 1:
            return rf"\sqrt{{{args[0]}}}"
        if name == "abs" and len(args) == 1:
            return rf"\left|{args[0]}\right|"
        if name == "log" and len(args) == 1:
            return rf"\ln\left({args[0]}\right)"
        if name in {"sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh"}:
            latex_name = {
                "asin": r"\arcsin",
                "acos": r"\arccos",
                "atan": r"\arctan",
            }.get(name, "\\" + name)
            return latex_name + r"\left(" + ",".join(args) + r"\right)"
        return rf"\operatorname{{{name}}}\left(" + ",".join(args) + r"\right)"
    raise MathExpressionError(f"cannot render LaTeX for {type(node).__name__}")


def expression_to_latex(expression: str) -> str:
    tree = _parse_expression(normalize_math_text(expression))
    return _latex_node(tree.body)


def _names(tree: ast.Expression) -> set[str]:
    function_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id not in function_names
        and node.id not in _ALLOWED_CONSTANTS
    }


def _features(tree: ast.Expression) -> dict[str, Any]:
    functions = sorted(
        {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
    )
    operators = []
    powers = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            operators.append(type(node.op).__name__)
            powers += int(isinstance(node.op, ast.Pow))
        elif isinstance(node, ast.UnaryOp):
            operators.append(type(node.op).__name__)
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "operator_count": len(operators),
        "operators": sorted(set(operators)),
        "function_count": len(functions),
        "functions": functions,
        "power_count": powers,
    }


@dataclass(frozen=True)
class ParsedEquation:
    original: str
    normalized: str
    equation_kind: str
    lhs: str
    rhs: str
    dependent_variable: str | None
    declared_arguments: tuple[str, ...]
    free_symbols: tuple[str, ...]
    feature_summary: Mapping[str, Any]
    display_latex: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cace-equation-object-v1",
            "original": self.original,
            "normalized": self.normalized,
            "display_latex": self.display_latex,
            "equation_kind": self.equation_kind,
            "lhs": self.lhs,
            "rhs": self.rhs,
            "dependent_variable": self.dependent_variable,
            "declared_arguments": list(self.declared_arguments),
            "free_symbols": list(self.free_symbols),
            "feature_summary": dict(self.feature_summary),
            "safe_expression_language": "cace-math-expression-v1",
            "evidence_authority": False,
            "proof_effect": "none",
            "promotion_authority": False,
        }


def parse_equation(text: str) -> ParsedEquation:
    normalized = normalize_math_text(text)
    function_match = _FUNCTION_DEF.fullmatch(normalized)
    if function_match:
        function_name = function_match.group(1)
        raw_args = function_match.group(2).strip()
        args = tuple(
            arg.strip()
            for arg in raw_args.split(",")
            if arg.strip()
        )
        if not args or len(set(args)) != len(args):
            raise MathExpressionError("function definition arguments must be unique and non-empty")
        if any(not _SAFE_NAME.fullmatch(arg) for arg in args):
            raise MathExpressionError("invalid function argument")
        rhs_tree = _parse_expression(function_match.group(3))
        free = _names(rhs_tree)
        return ParsedEquation(
            original=text,
            normalized=f"{function_name}({', '.join(args)}) = {_canonical(rhs_tree)}",
            equation_kind="function_definition",
            lhs=f"{function_name}({', '.join(args)})",
            rhs=_canonical(rhs_tree),
            dependent_variable=function_name,
            declared_arguments=args,
            free_symbols=tuple(sorted(free - set(args))),
            feature_summary=_features(rhs_tree),
            display_latex=(
                function_name
                + r"\left("
                + ",".join(args)
                + r"\right)="
                + _latex_node(rhs_tree.body)
            ),
        )

    if normalized.count("=") > 1:
        raise MathExpressionError("equation may contain at most one equals sign")

    if "=" in normalized:
        lhs_text, rhs_text = (part.strip() for part in normalized.split("=", 1))
        lhs_tree = _parse_expression(lhs_text)
        rhs_tree = _parse_expression(rhs_text)
        lhs = _canonical(lhs_tree)
        rhs = _canonical(rhs_tree)
        dependent = lhs if isinstance(lhs_tree.body, ast.Name) else None
        free = (_names(lhs_tree) | _names(rhs_tree))
        if dependent:
            free.discard(dependent)
            kind = "explicit"
        else:
            kind = "implicit"
        feature = _features(rhs_tree)
        lhs_feature = _features(lhs_tree)
        feature = {
            "ast_node_count": feature["ast_node_count"] + lhs_feature["ast_node_count"],
            "operator_count": feature["operator_count"] + lhs_feature["operator_count"],
            "operators": sorted(set(feature["operators"]) | set(lhs_feature["operators"])),
            "function_count": len(set(feature["functions"]) | set(lhs_feature["functions"])),
            "functions": sorted(set(feature["functions"]) | set(lhs_feature["functions"])),
            "power_count": feature["power_count"] + lhs_feature["power_count"],
        }
        return ParsedEquation(
            original=text,
            normalized=f"{lhs} = {rhs}",
            equation_kind=kind,
            lhs=lhs,
            rhs=rhs,
            dependent_variable=dependent,
            declared_arguments=(),
            free_symbols=tuple(sorted(free)),
            feature_summary=feature,
            display_latex=_latex_node(lhs_tree.body) + "=" + _latex_node(rhs_tree.body),
        )

    tree = _parse_expression(normalized)
    canonical = _canonical(tree)
    return ParsedEquation(
        original=text,
        normalized=canonical,
        equation_kind="expression",
        lhs="",
        rhs=canonical,
        dependent_variable=None,
        declared_arguments=(),
        free_symbols=tuple(sorted(_names(tree))),
        feature_summary=_features(tree),
        display_latex=_latex_node(tree.body),
    )


def _evaluate_node(node: ast.AST, env: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTANTS:
            return _ALLOWED_CONSTANTS[node.id]
        if node.id not in env:
            raise MathExpressionError(f"missing value for symbol: {node.id}")
        return env[node.id]
    if isinstance(node, ast.UnaryOp):
        value = _evaluate_node(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.USub):
            return -value
    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left, env)
        right = _evaluate_node(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        if isinstance(node.op, ast.Mod):
            return left % right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _ALLOWED_FUNCTIONS[node.func.id]
        args = [_evaluate_node(arg, env) for arg in node.args]
        return fn(*args)
    raise MathExpressionError(f"unsupported evaluator node: {type(node).__name__}")


def evaluate_expression(expression: str, environment: Mapping[str, Any]) -> Any:
    tree = _parse_expression(normalize_math_text(expression))
    with np.errstate(all="ignore"):
        return _evaluate_node(tree.body, environment)


def equation_features(equation_object: Mapping[str, Any]) -> dict[str, Any]:
    if equation_object.get("schema") != "cace-equation-object-v1":
        raise MathExpressionError("unsupported equation object schema")
    parsed = parse_equation(str(equation_object["normalized"]))
    summary = dict(parsed.feature_summary)
    symbols = list(parsed.free_symbols)
    free = set(symbols)
    coordinate_symbols = sorted(free & {"x", "y", "z"})
    parameter_candidates = sorted(free - {"x", "y", "z"})
    if parsed.equation_kind == "function_definition":
        coordinate_symbols = list(parsed.declared_arguments)
        parameter_candidates = sorted(free)
    explicit_2d = (
        parsed.equation_kind == "explicit"
        and parsed.dependent_variable in {"x", "y"}
        and len(free & ({"x", "y"} - {parsed.dependent_variable})) == 1
    ) or (
        parsed.equation_kind == "function_definition"
        and len(parsed.declared_arguments) == 1
    )
    explicit_3d = (
        parsed.equation_kind == "explicit"
        and parsed.dependent_variable in {"x", "y", "z"}
        and len(free & ({"x", "y", "z"} - {parsed.dependent_variable})) == 2
    ) or (
        parsed.equation_kind == "function_definition"
        and len(parsed.declared_arguments) == 2
    )
    summary.update(
        {
            "equation_kind": parsed.equation_kind,
            "dependent_variable": parsed.dependent_variable,
            "free_symbols": symbols,
            "symbol_count": len(symbols),
            "coordinate_symbols": coordinate_symbols,
            "parameter_candidates": parameter_candidates,
            "graphability": {
                "explicit_2d": explicit_2d,
                "explicit_3d": explicit_3d,
                "implicit_2d": parsed.equation_kind == "implicit"
                and {"x", "y"} <= free,
                "implicit_3d": parsed.equation_kind == "implicit"
                and {"x", "y", "z"} <= free,
            },
            "ai_summary_authority": False,
            "evidence_authority": False,
            "proof_effect": "none",
        }
    )
    return summary
