from __future__ import annotations

import math

import numpy as np
import pytest

from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.core.types import EvidenceKind, Maturity
from cace_studio.modules.research_geometry import (
    AdaptiveProductDimension,
    CurvedShearCell2D,
    DyadicPrefixCell,
    adaptive_prefix_dimension,
    curved_shear_inverse,
    curved_shear_map,
    interleaved_dyadic_bounds,
)


def test_interleaved_dyadic_bounds_are_exact_integer_cells():
    lower, upper, denominator = interleaved_dyadic_bounds(2, 3, "011001")
    assert denominator == 8
    np.testing.assert_array_equal(upper, lower + 1)
    assert np.all(lower >= 0)
    assert np.all(upper <= denominator)


def test_dyadic_module_reports_closed_form_tail_diameter():
    module = DyadicPrefixCell()
    params = module.resolved_params(
        {"dimensions": 3, "bits_per_axis": 4, "address": "010101010101"}
    )
    ctx = ExecutionContext(run_id="dyadic", seed=0)
    output = module.execute({}, params, ctx)
    assert output["denominator"] == 16
    assert output["cell_diameter"] == pytest.approx(math.sqrt(3) / 16.0)
    assert all(record.passed for record in module.verify({}, params, output, ctx))
    assert EvidenceKind.FORMAL not in module.proof_status.evidence
    assert module.metadata.maturity is Maturity.EXPERIMENTAL


def test_dyadic_address_drift_is_rejected():
    module = DyadicPrefixCell()
    with pytest.raises(ValidationError):
        module.validate({}, {"dimensions": 3, "bits_per_axis": 2, "address": "0101"})
    with pytest.raises(ValidationError):
        module.validate({}, {"dimensions": 2, "bits_per_axis": 2, "address": "01x1"})


def test_adaptive_dimension_returns_minimal_prefix_for_tail_bound():
    widths = np.array([1.0, 0.25, 0.125, 0.0625])
    retained, bound = adaptive_prefix_dimension(widths, 0.14)
    assert retained == 2
    assert bound == pytest.approx(math.sqrt(0.125**2 + 0.0625**2))
    assert math.sqrt(float(np.sum(widths[retained - 1 :] ** 2))) > 0.14


def test_adaptive_dimension_module_verifies_its_geometric_scope_only():
    module = AdaptiveProductDimension()
    widths = np.array([1.0, 0.2, 0.05, 0.01])
    params = module.resolved_params({"tolerance": 0.06})
    ctx = ExecutionContext(run_id="adaptive", seed=0)
    output = module.execute({"widths": widths}, params, ctx)
    records = module.verify({"widths": widths}, params, output, ctx)
    assert all(record.passed for record in records)
    assert output["retained_dimensions"] == 2
    assert "model-output error" in module.proof_status.limitations[0]


def test_curved_shear_has_explicit_inverse_and_unit_jacobian():
    points = np.array(
        [
            [0.0, 0.0],
            [0.25, 0.5],
            [1.0, 1.0],
            [0.9, 0.2],
        ]
    )
    mapped = curved_shear_map(points, shear=0.7, curvature=-0.4)
    recovered = curved_shear_inverse(mapped, shear=0.7, curvature=-0.4)
    np.testing.assert_allclose(recovered, points, atol=2e-16, rtol=0.0)

    module = CurvedShearCell2D()
    params = module.resolved_params({"shear": 0.7, "curvature": -0.4, "samples_per_edge": 32})
    ctx = ExecutionContext(run_id="shear", seed=0)
    output = module.execute({}, params, ctx)
    assert output["jacobian_determinant"] == 1.0
    assert output["area"] == 1.0
    assert all(record.passed for record in module.verify({}, params, output, ctx))


def test_curved_shear_animation_payload_reuses_computed_boundary():
    module = CurvedShearCell2D()
    params = module.resolved_params(
        {"shear": 0.4, "curvature": 0.2, "samples_per_edge": 12}
    )
    ctx = ExecutionContext(run_id="shear-animation", seed=0)
    output = module.execute({}, params, ctx)
    payload = module.animation_payload(params, output)

    assert payload is not None
    assert payload["kind"] == "transform2d"
    assert payload["closed"] is True
    np.testing.assert_array_equal(payload["target"], output["boundary"])
    source = np.asarray(payload["source"], dtype=float)
    assert source.shape == np.asarray(output["boundary"]).shape
    assert source.shape == (48, 2)
    assert payload["evidence_role"].startswith("presentation only")


def test_geometry_resource_and_parameter_limits_fail_closed():
    adaptive = AdaptiveProductDimension()
    with pytest.raises(ValidationError):
        adaptive.validate({"widths": [1.0, -0.1]}, {"tolerance": 0.1})

    shear = CurvedShearCell2D()
    with pytest.raises(ValidationError):
        shear.validate({}, {"samples_per_edge": 1})
    with pytest.raises(ValidationError):
        shear.validate({}, {"curvature": float("nan")})
