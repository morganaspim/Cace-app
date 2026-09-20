from __future__ import annotations

import json
import math
from typing import Any

import numpy as np

from cace_studio.core.expression_math import (
    MathExpressionError,
    equation_features,
    evaluate_expression,
    parse_equation,
)
from cace_studio.core.module import ExecutionContext, Module, ValidationError
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


def _numeric_parameters(text: str) -> dict[str, float]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("parameters_json must be a JSON object") from exc
    if not isinstance(raw, dict):
        raise ValidationError("parameters_json must be a JSON object")
    out: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key or len(key) > 32:
            raise ValidationError("parameter names must be short non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"parameter {key!r} must be numeric")
        number = float(value)
        if not math.isfinite(number):
            raise ValidationError(f"parameter {key!r} must be finite")
        out[key] = number
    return out


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    return value


def _equation_record(name: str, ok: bool, statement: str, details: dict[str, Any] | None = None):
    return VerificationRecord(
        name,
        EvidenceKind.NUMERICAL,
        statement,
        VerificationState.PASS if ok else VerificationState.FAIL,
        "CACE safe-expression structural/numerical check",
        details or {},
    )


class CustomEquation(Module):
    metadata = ModuleMetadata(
        "math.custom_equation",
        "Custom Equation",
        "1.0.0",
        "Mathematics",
        "Parse user-entered mathematical notation into a safe first-class CACE equation object.",
        Maturity.BETA,
        assumptions=("input uses the documented CACE math expression language",),
    )
    outputs = (PortSpec("equation", "equation_object"),)
    parameters = (
        ParameterSpec(
            "equation",
            "string",
            "y = sin(x)",
            "Equation or expression. Common symbols such as ^, π, ×, ÷ and ln(...) are normalized.",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "safe mathematical expression subset; not arbitrary Python",
            "parsing/sampling is not formal proof",
        ],
    )

    def execute(self, inputs, params, ctx):
        text = str(self.resolved_params(params)["equation"])
        try:
            return {"equation": parse_equation(text).to_dict()}
        except MathExpressionError as exc:
            raise ValidationError(str(exc)) from exc

    def verify(self, inputs, params, outputs, ctx):
        obj = outputs["equation"]
        ok = (
            isinstance(obj, dict)
            and obj.get("schema") == "cace-equation-object-v1"
            and obj.get("evidence_authority") is False
            and obj.get("proof_effect") == "none"
        )
        return [_equation_record("safe-equation-object", ok, "equation parsed into the safe CACE equation envelope")]


class EquationFeatureSummary(Module):
    metadata = ModuleMetadata(
        "math.equation_features",
        "Equation Feature Summary",
        "1.0.0",
        "Mathematics",
        "Extract structural features from a CACE equation for UI, Grow, and local-AI summarization.",
        Maturity.BETA,
    )
    inputs = (PortSpec("equation", "equation_object"),)
    outputs = (PortSpec("features", "equation_features"),)
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["features describe syntax/graphability and are not theorem claims"],
    )

    def execute(self, inputs, params, ctx):
        try:
            return {"features": equation_features(inputs["equation"])}
        except MathExpressionError as exc:
            raise ValidationError(str(exc)) from exc

    def verify(self, inputs, params, outputs, ctx):
        features = outputs["features"]
        ok = isinstance(features, dict) and features.get("proof_effect") == "none"
        return [_equation_record("equation-feature-summary", ok, "equation structural features were extracted without evidence promotion")]


class GraphEquation2D(Module):
    metadata = ModuleMetadata(
        "math.graph_equation_2d",
        "Graph Equation 2D",
        "1.0.0",
        "Visualization",
        "Sample an explicit or implicit CACE equation for deterministic 2D graph rendering.",
        Maturity.BETA,
        assumptions=("requested graph form is supported", "ranges are finite and ordered"),
    )
    inputs = (PortSpec("equation", "equation_object"),)
    outputs = (PortSpec("graph", "equation_plot_2d"),)
    parameters = (
        ParameterSpec("x_min", "number", -10.0),
        ParameterSpec("x_max", "number", 10.0),
        ParameterSpec("y_min", "number", -10.0),
        ParameterSpec("y_max", "number", 10.0),
        ParameterSpec("samples", "integer", 401),
        ParameterSpec(
            "parameters_json",
            "string",
            "{}",
            "Numeric values for free parameters, for example {\"a\":2,\"r\":4}.",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "finite numerical sampling",
            "implicit curves require renderer contouring at residual=0",
            "sampling does not prove global curve properties",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        if not math.isfinite(float(p["x_min"])) or not math.isfinite(float(p["x_max"])):
            raise ValidationError("x range must be finite")
        if not math.isfinite(float(p["y_min"])) or not math.isfinite(float(p["y_max"])):
            raise ValidationError("y range must be finite")
        if float(p["x_min"]) >= float(p["x_max"]) or float(p["y_min"]) >= float(p["y_max"]):
            raise ValidationError("graph ranges must be ordered")
        if not 32 <= int(p["samples"]) <= 2000:
            raise ValidationError("samples must be between 32 and 2000")

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        try:
            parsed = parse_equation(str(inputs["equation"]["normalized"]))
        except (KeyError, MathExpressionError) as exc:
            raise ValidationError(str(exc)) from exc

        count = int(p["samples"])
        parameters = _numeric_parameters(str(p["parameters_json"]))

        if parsed.equation_kind in {"explicit", "function_definition"}:
            dependent = parsed.dependent_variable
            declared = set(parsed.declared_arguments)
            free = set(parsed.free_symbols)
            if parsed.equation_kind == "function_definition":
                if len(parsed.declared_arguments) != 1:
                    raise ValidationError("2D function graph requires exactly one declared argument")
                independent = parsed.declared_arguments[0]
                dependent = parsed.dependent_variable or "f"
            else:
                if dependent not in {"x", "y"}:
                    raise ValidationError("2D explicit graph requires x=... or y=...")
                allowed = {"x", "y"} - {dependent}
                candidates = sorted(free & allowed)
                if len(candidates) != 1:
                    raise ValidationError("2D explicit graph requires exactly one independent x/y symbol")
                independent = candidates[0]

            needed_parameters = (
                set(parsed.free_symbols) - {independent}
                if parsed.equation_kind == "function_definition"
                else set(parsed.free_symbols) - {independent}
            )
            missing_parameters = sorted(needed_parameters - set(parameters))
            if missing_parameters:
                raise ValidationError(
                    f"missing numeric parameter values: {missing_parameters}"
                )
            unknown_parameters = sorted(set(parameters) - needed_parameters)
            if unknown_parameters:
                raise ValidationError(
                    f"unused numeric parameters: {unknown_parameters}"
                )

            sample = np.linspace(
                float(p["x_min"]) if independent != "y" else float(p["y_min"]),
                float(p["x_max"]) if independent != "y" else float(p["y_max"]),
                count,
            )
            env = {independent: sample, **parameters}
            try:
                values = np.asarray(evaluate_expression(parsed.rhs, env), dtype=float)
            except (MathExpressionError, FloatingPointError, ValueError, TypeError) as exc:
                raise ValidationError(f"equation evaluation failed: {exc}") from exc
            if values.ndim == 0:
                values = np.full_like(sample, float(values))
            if values.shape != sample.shape:
                raise ValidationError("2D explicit equation did not produce one value per sample")
            points = (
                np.column_stack([values, sample])
                if dependent == "x"
                else np.column_stack([sample, values])
            )
            return {
                "graph": {
                    "schema": "cace-equation-plot-2d-v1",
                    "mode": "explicit",
                    "equation": inputs["equation"],
                    "independent_variable": independent,
                    "dependent_variable": dependent,
                    "points": _json_value(points),
                    "parameter_values": parameters,
                    "nonfinite_count": int(np.size(values) - np.count_nonzero(np.isfinite(values))),
                    "presentation_only": True,
                    "evidence_authority": False,
                    "proof_effect": "none",
                }
            }

        if parsed.equation_kind == "implicit":
            symbols = set(parsed.free_symbols)
            if not {"x", "y"} <= symbols:
                raise ValidationError("2D implicit graph requires both x and y")
            needed_parameters = symbols - {"x", "y"}
            missing_parameters = sorted(needed_parameters - set(parameters))
            if missing_parameters:
                raise ValidationError(
                    f"missing numeric parameter values: {missing_parameters}"
                )
            unknown_parameters = sorted(set(parameters) - needed_parameters)
            if unknown_parameters:
                raise ValidationError(
                    f"unused numeric parameters: {unknown_parameters}"
                )
            grid_count = min(count, 600)
            x = np.linspace(float(p["x_min"]), float(p["x_max"]), grid_count)
            y = np.linspace(float(p["y_min"]), float(p["y_max"]), grid_count)
            xx, yy = np.meshgrid(x, y)
            env = {"x": xx, "y": yy, **parameters}
            try:
                lhs = evaluate_expression(parsed.lhs, env)
                rhs = evaluate_expression(parsed.rhs, env)
                residual = np.asarray(lhs - rhs, dtype=float)
            except (MathExpressionError, FloatingPointError, ValueError, TypeError) as exc:
                raise ValidationError(f"implicit equation evaluation failed: {exc}") from exc
            if residual.shape != xx.shape:
                residual = np.broadcast_to(residual, xx.shape).astype(float, copy=False)
            return {
                "graph": {
                    "schema": "cace-equation-plot-2d-v1",
                    "mode": "implicit_contour",
                    "equation": inputs["equation"],
                    "x": _json_value(x),
                    "y": _json_value(y),
                    "residual": _json_value(residual),
                    "parameter_values": parameters,
                    "contour_level": 0.0,
                    "nonfinite_count": int(np.size(residual) - np.count_nonzero(np.isfinite(residual))),
                    "presentation_only": True,
                    "evidence_authority": False,
                    "proof_effect": "none",
                }
            }

        raise ValidationError("expression-only input is not directly graphable; write an equation such as y=...")

    def verify(self, inputs, params, outputs, ctx):
        graph = outputs["graph"]
        ok = graph.get("schema") == "cace-equation-plot-2d-v1" and graph.get("proof_effect") == "none"
        return [_equation_record("equation-2d-sampling", ok, "2D graph payload was produced by the safe numerical sampler")]


class GraphEquation3D(Module):
    metadata = ModuleMetadata(
        "math.graph_equation_3d",
        "Graph Equation 3D",
        "1.0.0",
        "Visualization",
        "Sample an explicit surface z=f(x,y) or equivalent function definition for 3D rendering.",
        Maturity.BETA,
        assumptions=("surface has two independent variables", "ranges are finite and ordered"),
    )
    inputs = (PortSpec("equation", "equation_object"),)
    outputs = (PortSpec("surface", "equation_plot_3d"),)
    parameters = (
        ParameterSpec("x_min", "number", -5.0),
        ParameterSpec("x_max", "number", 5.0),
        ParameterSpec("y_min", "number", -5.0),
        ParameterSpec("y_max", "number", 5.0),
        ParameterSpec("samples", "integer", 81),
        ParameterSpec(
            "parameters_json",
            "string",
            "{}",
            "Numeric values for free parameters, for example {\"a\":2}.",
        ),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "explicit two-variable surfaces only in v1",
            "finite numerical sampling",
            "rendering is presentation-only",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        if float(p["x_min"]) >= float(p["x_max"]) or float(p["y_min"]) >= float(p["y_max"]):
            raise ValidationError("surface ranges must be ordered")
        if not 16 <= int(p["samples"]) <= 300:
            raise ValidationError("3D samples must be between 16 and 300")

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        try:
            parsed = parse_equation(str(inputs["equation"]["normalized"]))
        except (KeyError, MathExpressionError) as exc:
            raise ValidationError(str(exc)) from exc

        if parsed.equation_kind == "function_definition":
            if len(parsed.declared_arguments) != 2:
                raise ValidationError("3D function graph requires exactly two declared arguments")
            variables = tuple(parsed.declared_arguments)
            dependent = parsed.dependent_variable or "f"
        elif parsed.equation_kind == "explicit":
            dependent = parsed.dependent_variable
            if dependent != "z":
                raise ValidationError("3D v1 explicit graph requires z = f(x,y)")
            candidates = tuple(sorted(set(parsed.free_symbols) & {"x", "y"}))
            if set(candidates) != {"x", "y"}:
                raise ValidationError("3D v1 explicit graph requires both x and y")
            variables = ("x", "y")
        else:
            raise ValidationError("3D v1 requires an explicit two-variable surface such as z=sin(x)*cos(y)")

        parameters = _numeric_parameters(str(p["parameters_json"]))
        needed_parameters = set(parsed.free_symbols) - set(variables)
        missing_parameters = sorted(needed_parameters - set(parameters))
        if missing_parameters:
            raise ValidationError(
                f"missing numeric parameter values: {missing_parameters}"
            )
        unknown_parameters = sorted(set(parameters) - needed_parameters)
        if unknown_parameters:
            raise ValidationError(
                f"unused numeric parameters: {unknown_parameters}"
            )

        count = int(p["samples"])
        u = np.linspace(float(p["x_min"]), float(p["x_max"]), count)
        v = np.linspace(float(p["y_min"]), float(p["y_max"]), count)
        uu, vv = np.meshgrid(u, v)
        env = {variables[0]: uu, variables[1]: vv, **parameters}
        try:
            values = np.asarray(
                evaluate_expression(parsed.rhs, env),
                dtype=float,
            )
        except (MathExpressionError, FloatingPointError, ValueError, TypeError) as exc:
            raise ValidationError(f"surface evaluation failed: {exc}") from exc
        if values.ndim == 0:
            values = np.full_like(uu, float(values))
        if values.shape != uu.shape:
            raise ValidationError("surface equation did not produce the expected sample grid")

        coordinates = {
            variables[0]: uu.tolist(),
            variables[1]: vv.tolist(),
            dependent: values.tolist(),
        }
        return {
            "surface": {
                "schema": "cace-equation-plot-3d-v1",
                "mode": "explicit_surface",
                "equation": inputs["equation"],
                "independent_variables": list(variables),
                "dependent_variable": dependent,
                "coordinates": _json_value(coordinates),
                "parameter_values": parameters,
                "nonfinite_count": int(np.size(values) - np.count_nonzero(np.isfinite(values))),
                "presentation_only": True,
                "evidence_authority": False,
                "proof_effect": "none",
            }
        }

    def verify(self, inputs, params, outputs, ctx):
        surface = outputs["surface"]
        ok = surface.get("schema") == "cace-equation-plot-3d-v1" and surface.get("proof_effect") == "none"
        return [_equation_record("equation-3d-sampling", ok, "3D surface payload was produced by the safe numerical sampler")]


EQUATION_MODULES = (
    CustomEquation,
    EquationFeatureSummary,
    GraphEquation2D,
    GraphEquation3D,
)


def register_equation_modules(registry):
    for cls in EQUATION_MODULES:
        registry.register(cls)
