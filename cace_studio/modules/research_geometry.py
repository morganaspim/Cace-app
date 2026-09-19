from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from cace_studio.core.module import Module, ExecutionContext, ValidationError
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


def interleaved_dyadic_bounds(
    dimensions: int,
    bits_per_axis: int,
    address: str,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Decode an interleaved bit prefix into an exact dyadic product cell.

    Bit position ``level * dimensions + axis`` is the next binary digit for that
    coordinate. Returned integer bounds share denominator ``2**bits_per_axis``.
    The representation is exact; no floating point is used for the cell identity.
    """
    if dimensions < 1:
        raise ValueError("dimensions must be positive")
    if bits_per_axis < 1:
        raise ValueError("bits_per_axis must be positive")
    expected = dimensions * bits_per_axis
    if len(address) != expected or any(bit not in "01" for bit in address):
        raise ValueError(f"address must contain exactly {expected} binary digits")

    numerators = np.zeros(dimensions, dtype=np.int64)
    for level in range(bits_per_axis):
        for axis in range(dimensions):
            numerators[axis] = 2 * numerators[axis] + int(address[level * dimensions + axis])
    denominator = 1 << bits_per_axis
    return numerators, numerators + 1, denominator


def adaptive_prefix_dimension(widths: np.ndarray, tolerance: float) -> tuple[int, float]:
    """Return minimal prefix dimension whose omitted Euclidean box tail is <= tolerance."""
    values = np.asarray(widths, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("widths must be a non-empty one-dimensional array")
    if np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("widths must be finite and non-negative")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative")

    # A product rectangle with omitted side lengths w_i has Euclidean diameter
    # sqrt(sum_i w_i^2). Find the smallest retained prefix meeting the bound.
    squared = values * values
    tail_squared = np.concatenate((np.cumsum(squared[::-1])[::-1], np.array([0.0])))
    for retained in range(values.size + 1):
        bound = math.sqrt(float(tail_squared[retained]))
        if bound <= tolerance:
            return retained, bound
    return int(values.size), 0.0


def curved_shear_map(points: np.ndarray, shear: float, curvature: float) -> np.ndarray:
    """Apply F(u,v)=(u+s*v+c*v*(1-v), v), an exactly area-preserving shear."""
    values = np.asarray(points, dtype=float)
    if values.shape[-1] != 2:
        raise ValueError("points must have trailing dimension 2")
    u = values[..., 0]
    v = values[..., 1]
    result = np.empty_like(values, dtype=float)
    result[..., 0] = u + shear * v + curvature * v * (1.0 - v)
    result[..., 1] = v
    return result


def curved_shear_inverse(points: np.ndarray, shear: float, curvature: float) -> np.ndarray:
    values = np.asarray(points, dtype=float)
    if values.shape[-1] != 2:
        raise ValueError("points must have trailing dimension 2")
    x = values[..., 0]
    y = values[..., 1]
    result = np.empty_like(values, dtype=float)
    result[..., 0] = x - shear * y - curvature * y * (1.0 - y)
    result[..., 1] = y
    return result


class DyadicPrefixCell(Module):
    metadata = ModuleMetadata(
        "research.dyadic_prefix_cell",
        "Tail-Certified Dyadic Prefix Cell",
        "0.1.0",
        "Research Geometry",
        "Exact integer representation of a finite-prefix dyadic product cell in [0,1]^d.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Address bits are interleaved by level then coordinate axis.",
            "This module certifies the dyadic product cell, not Hilbert-curve ordering or continuity.",
        ),
    )
    outputs = (
        PortSpec("lower_numerators", "array"),
        PortSpec("upper_numerators", "array"),
        PortSpec("denominator", "integer"),
        PortSpec("center", "array"),
        PortSpec("cell_diameter", "number"),
        PortSpec("max_coordinate_tail", "number"),
    )
    parameters = (
        ParameterSpec("dimensions", "integer", 2, "Number of coordinate axes, 1..32"),
        ParameterSpec("bits_per_axis", "integer", 4, "Binary prefix depth per axis, 1..30"),
        ParameterSpec("address", "string", "00000000", "Interleaved binary address of length dimensions*bits_per_axis"),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "Exact cell identity uses integers, but displayed center/diameter use binary64.",
            "No Hilbert ordering theorem is claimed; this is the exact dyadic addressing substrate for such work.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        dimensions = int(p["dimensions"])
        bits = int(p["bits_per_axis"])
        if not 1 <= dimensions <= 32:
            raise ValidationError("DyadicPrefixCell requires 1 <= dimensions <= 32")
        if not 1 <= bits <= 30:
            raise ValidationError("DyadicPrefixCell requires 1 <= bits_per_axis <= 30")
        try:
            interleaved_dyadic_bounds(dimensions, bits, str(p["address"]))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        lower, upper, denominator = interleaved_dyadic_bounds(
            int(params["dimensions"]), int(params["bits_per_axis"]), str(params["address"])
        )
        center = (lower.astype(float) + 0.5) / float(denominator)
        width = 1.0 / float(denominator)
        return {
            "lower_numerators": lower,
            "upper_numerators": upper,
            "denominator": int(denominator),
            "center": center,
            "cell_diameter": math.sqrt(int(params["dimensions"])) * width,
            "max_coordinate_tail": width,
        }

    def verify(self, inputs, params, outputs, ctx):
        lower = np.asarray(outputs["lower_numerators"], dtype=np.int64)
        upper = np.asarray(outputs["upper_numerators"], dtype=np.int64)
        denominator = int(outputs["denominator"])
        dimensions = int(params["dimensions"])
        bits = int(params["bits_per_axis"])
        exact = bool(
            denominator == 1 << bits
            and lower.shape == (dimensions,)
            and np.array_equal(upper, lower + 1)
            and np.all(lower >= 0)
            and np.all(upper <= denominator)
        )
        expected_diameter = math.sqrt(dimensions) / denominator
        diameter_ok = math.isclose(
            float(outputs["cell_diameter"]), expected_diameter, rel_tol=0.0, abs_tol=1e-15
        )
        return [
            VerificationRecord(
                "dyadic-prefix-integer-cell",
                EvidenceKind.NUMERICAL,
                "integer dyadic bounds form one exact level-n product cell",
                VerificationState.PASS if exact else VerificationState.FAIL,
                "integer denominator and unit-numerator-width checks",
                {"denominator": denominator, "bits_per_axis": bits, "dimensions": dimensions},
                notes=("The cell identity is exact integer arithmetic; this runtime record is not formal proof evidence.",),
            ),
            VerificationRecord(
                "dyadic-prefix-tail-bound",
                EvidenceKind.NUMERICAL,
                "reported Euclidean cell diameter equals sqrt(d)/2^n",
                VerificationState.PASS if diameter_ok else VerificationState.FAIL,
                "closed-form product-box diameter check",
                {"cell_diameter": float(outputs["cell_diameter"]), "expected": expected_diameter},
            ),
        ]


class AdaptiveProductDimension(Module):
    metadata = ModuleMetadata(
        "research.adaptive_product_dimension",
        "Adaptive Product Dimension",
        "0.1.0",
        "Research Geometry",
        "Choose the smallest retained prefix whose omitted product-box tail diameter is within tolerance.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Input widths are ordered by the user's chosen coordinate importance.",
            "Omitted-factor error is measured by the Euclidean diameter bound sqrt(sum tail_width^2).",
        ),
    )
    inputs = (PortSpec("widths", "array"),)
    outputs = (
        PortSpec("retained_dimensions", "integer"),
        PortSpec("tail_bound", "number"),
        PortSpec("retained_widths", "array"),
        PortSpec("omitted_widths", "array"),
    )
    parameters = (
        ParameterSpec("tolerance", "number", 0.01, "Maximum allowed omitted Euclidean diameter"),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "The truncation certificate concerns product-box geometry only, not model-output error.",
            "Coordinate ordering is supplied externally and is not optimized by this module.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        widths = np.asarray(inputs["widths"], dtype=float)
        try:
            adaptive_prefix_dimension(widths, float(self.resolved_params(params)["tolerance"]))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        widths = np.asarray(inputs["widths"], dtype=float)
        retained, bound = adaptive_prefix_dimension(widths, float(params["tolerance"]))
        return {
            "retained_dimensions": retained,
            "tail_bound": bound,
            "retained_widths": widths[:retained],
            "omitted_widths": widths[retained:],
        }

    def verify(self, inputs, params, outputs, ctx):
        widths = np.asarray(inputs["widths"], dtype=float)
        retained = int(outputs["retained_dimensions"])
        actual = math.sqrt(float(np.sum(widths[retained:] ** 2)))
        tolerance = float(params["tolerance"])
        minimal = retained == 0 or math.sqrt(float(np.sum(widths[retained - 1:] ** 2))) > tolerance
        ok = actual <= tolerance + 1e-15 and minimal
        return [
            VerificationRecord(
                "adaptive-product-tail-bound",
                EvidenceKind.NUMERICAL,
                "retained prefix is minimal and omitted Euclidean product-box diameter is within tolerance",
                VerificationState.PASS if ok else VerificationState.FAIL,
                "direct tail sum-of-squares recomputation",
                {"retained_dimensions": retained, "tail_bound": actual, "tolerance": tolerance},
            )
        ]


class CurvedShearCell2D(Module):
    metadata = ModuleMetadata(
        "research.curved_shear_cell_2d",
        "Curved Shear Cell 2D",
        "0.1.0",
        "Research Geometry",
        "Sample an explicitly invertible curved shear of the unit square with determinant-one Jacobian.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Map is F(u,v)=(u+s v+c v(1-v), v).",
            "Its inverse is (x,y)->(x-s y-c y(1-y), y).",
            "Jacobian determinant is identically one for all finite shear and curvature parameters.",
        ),
    )
    outputs = (
        PortSpec("boundary", "array"),
        PortSpec("jacobian_determinant", "number"),
        PortSpec("area", "number"),
        PortSpec("inverse_max_residual", "number"),
    )
    parameters = (
        ParameterSpec("shear", "number", 0.5, "Linear shear coefficient"),
        ParameterSpec("curvature", "number", 0.25, "Quadratic vertical coupling coefficient"),
        ParameterSpec("samples_per_edge", "integer", 65, "Boundary samples per edge, 2..4096"),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "Area preservation follows from this specific triangular polynomial map; arbitrary curved cells are not covered.",
            "The runtime inverse residual is numerical evidence, not a formal diffeomorphism proof artifact.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        for name in ("shear", "curvature"):
            if not math.isfinite(float(p[name])):
                raise ValidationError(f"CurvedShearCell2D requires finite {name}")
        samples = int(p["samples_per_edge"])
        if not 2 <= samples <= 4096:
            raise ValidationError("CurvedShearCell2D requires 2 <= samples_per_edge <= 4096")

    def execute(self, inputs, params, ctx):
        shear = float(params["shear"])
        curvature = float(params["curvature"])
        samples = int(params["samples_per_edge"])
        t = np.linspace(0.0, 1.0, samples)
        boundary_unit = np.concatenate(
            [
                np.column_stack((t, np.zeros_like(t))),
                np.column_stack((np.ones_like(t), t)),
                np.column_stack((t[::-1], np.ones_like(t))),
                np.column_stack((np.zeros_like(t), t[::-1])),
            ],
            axis=0,
        )
        boundary = curved_shear_map(boundary_unit, shear, curvature)
        recovered = curved_shear_inverse(boundary, shear, curvature)
        residual = float(np.max(np.abs(recovered - boundary_unit)))
        return {
            "boundary": boundary,
            "jacobian_determinant": 1.0,
            "area": 1.0,
            "inverse_max_residual": residual,
        }

    def animation_payload(self, params, outputs):
        samples = int(params["samples_per_edge"])
        t = np.linspace(0.0, 1.0, samples)
        boundary_unit = np.concatenate(
            [
                np.column_stack((t, np.zeros_like(t))),
                np.column_stack((np.ones_like(t), t)),
                np.column_stack((t[::-1], np.ones_like(t))),
                np.column_stack((np.zeros_like(t), t[::-1])),
            ],
            axis=0,
        )
        boundary = np.asarray(outputs["boundary"], dtype=float)
        return {
            "kind": "transform2d",
            "title": "Curved Shear Cell 2D",
            "source": boundary_unit,
            "target": boundary,
            "closed": True,
            "duration_ms": 1100,
            "evidence_role": "presentation only; verification uses the original module outputs",
        }

    def verify(self, inputs, params, outputs, ctx):
        residual = float(outputs["inverse_max_residual"])
        finite = bool(np.all(np.isfinite(np.asarray(outputs["boundary"], dtype=float))))
        ok = finite and residual <= 5e-15 and float(outputs["jacobian_determinant"]) == 1.0
        return [
            VerificationRecord(
                "curved-shear-inverse-and-jacobian",
                EvidenceKind.NUMERICAL,
                "sampled curved shear is finite, numerically invertible, and reports determinant-one Jacobian",
                VerificationState.PASS if ok else VerificationState.FAIL,
                "explicit inverse round-trip plus analytic triangular-Jacobian identity",
                {"inverse_max_residual": residual, "jacobian_determinant": 1.0, "area": 1.0},
                notes=("The determinant identity is analytic for this formula; this runtime record is still not FORMAL evidence.",),
            )
        ]


def register_research_geometry(registry) -> None:
    for cls in (DyadicPrefixCell, AdaptiveProductDimension, CurvedShearCell2D):
        registry.register(cls)
