from __future__ import annotations

import math

import numpy as np
import pytest

from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.core.types import EvidenceKind, Maturity
from cace_studio.modules.research_dynamics import (
    GrowthRotationRandomWalk,
    plane_rotation_matrix,
)


def resolved(**overrides):
    module = GrowthRotationRandomWalk()
    return module.resolved_params(overrides)


def test_plane_rotation_is_orthogonal_in_arbitrary_dimension():
    rotation = plane_rotation_matrix(7, 2, 5, 0.37)
    np.testing.assert_allclose(rotation.T @ rotation, np.eye(7), atol=1e-14, rtol=0.0)
    assert np.linalg.det(rotation) == pytest.approx(1.0, abs=1e-14)


def test_pi_rotation_negates_selected_plane_and_fixes_complement():
    rotation = plane_rotation_matrix(5, 1, 3, math.pi)
    vector = np.array([2.0, 3.0, 5.0, 7.0, 11.0])
    transformed = rotation @ vector
    np.testing.assert_allclose(
        transformed,
        np.array([2.0, -3.0, 5.0, -7.0, 11.0]),
        atol=1e-14,
        rtol=0.0,
    )


def test_walk_is_deterministic_for_same_experiment_seed():
    module = GrowthRotationRandomWalk()
    params = resolved(dimensions=4, steps=16, dt=0.05, noise_scale=0.3)
    first = module.execute({}, params, ExecutionContext(run_id="a", seed=17))
    second = module.execute({}, params, ExecutionContext(run_id="b", seed=17))
    different = module.execute({}, params, ExecutionContext(run_id="c", seed=18))
    np.testing.assert_array_equal(first["trajectory"], second["trajectory"])
    assert not np.array_equal(first["trajectory"], different["trajectory"])
    assert first["seed"] == 17


def test_zero_noise_matches_closed_form_growth_rotation_iteration():
    module = GrowthRotationRandomWalk()
    params = resolved(
        dimensions=3,
        steps=8,
        dt=0.1,
        log_growth_rate=0.2,
        rotation_angle=0.25,
        axis_a=0,
        axis_b=2,
        noise_scale=0.0,
        initial_radius=2.0,
    )
    result = module.execute({}, params, ExecutionContext(run_id="closed", seed=9))
    rotation = plane_rotation_matrix(3, 0, 2, 0.25)
    factor = math.exp(0.2 * 0.1)
    expected = np.array([2.0, 0.0, 0.0])
    for step in range(8):
        expected = factor * (rotation @ expected)
        np.testing.assert_allclose(result["trajectory"][step + 1], expected, atol=1e-13, rtol=1e-13)


def test_runtime_verification_is_numerical_not_formal():
    module = GrowthRotationRandomWalk()
    params = resolved(dimensions=6, steps=12)
    ctx = ExecutionContext(run_id="verify", seed=3)
    outputs = module.execute({}, params, ctx)
    records = module.verify({}, params, outputs, ctx)
    assert records
    assert all(record.passed for record in records)
    assert all(record.kind is EvidenceKind.NUMERICAL for record in records)
    assert EvidenceKind.FORMAL not in module.proof_status.evidence
    assert module.metadata.maturity is Maturity.EXPERIMENTAL
    assert module.proof_status.formal_artifact is None


def test_invalid_dimension_axes_and_resource_bounds_fail_closed():
    module = GrowthRotationRandomWalk()
    with pytest.raises(ValidationError):
        module.validate({}, {"dimensions": 1})
    with pytest.raises(ValidationError):
        module.validate({}, {"dimensions": 3, "axis_a": 1, "axis_b": 1})
    with pytest.raises(ValidationError):
        module.validate({}, {"steps": 100_001})
    with pytest.raises(ValidationError):
        module.validate({}, {"dt": 0.0})
