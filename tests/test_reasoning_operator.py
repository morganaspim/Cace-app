from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cace_studio.core.reasoning import (
    DuplicateReasoningOperator,
    NativeReasoningBackendUnavailable,
    ReasoningOperator,
    ReasoningOperatorRegistry,
    ReasoningStep,
    UnknownReasoningOperator,
    build_exact_geometric_registry,
    evaluate_paired_intervention,
    evaluate_symmetry_reduction,
)


class _FakePermutation:
    def __init__(self, image=(0, 1, 2)):
        self.image = tuple(image)

    def inverse(self):
        inv = [0] * len(self.image)
        for i, value in enumerate(self.image):
            inv[value] = i
        return _FakePermutation(inv)

    def compose(self, inner):
        return _FakePermutation(
            tuple(self.image[inner.image[i]] for i in range(len(self.image)))
        )

    def act_coordinates(self, values):
        out = [None] * len(self.image)
        for i, target in enumerate(self.image):
            out[target] = values[i]
        return tuple(out)

    def act_exterior(self, value):
        return ("exterior-action", self.image, value)


class _FakeGroup:
    def canonical_coordinate_representative(self, values):
        return tuple(sorted(values))

    def canonical_exterior_representative(self, value):
        return ("canonical-exterior", value)


class _FakeExterior:
    def __init__(self, value):
        self.value = value

    def wedge(self, rhs):
        return ("wedge", self.value, rhs)

    def hodge_dual(self):
        return ("dual", self.value)

    def pushforward(self, linear):
        return ("pushforward", self.value, linear)


class _FakeAffine:
    def apply(self, point):
        return ("affine", tuple(point))


class _FakeSimplex:
    def barycentric_coordinates(self, point):
        return ("barycentric", tuple(point))


class _FakeNative:
    ExactPermutation = _FakePermutation
    FinitePermutationGroup = _FakeGroup
    ExactExterior = _FakeExterior
    ExactAffineMap = _FakeAffine
    ExactSimplex = _FakeSimplex


def _simple_operator(operator_id="test.increment"):
    return ReasoningOperator(
        operator_id=operator_id,
        version="1",
        title="Increment",
        input_types=("integer",),
        output_type="integer",
        implementation_ref="test",
        invariants=("adds one",),
        cost_class="constant",
    )


def test_reasoning_operator_has_no_evidence_authority():
    op = _simple_operator()
    assert op.evidence_authority is False
    assert op.descriptor()["evidence_authority"] is False
    assert len(op.semantic_sha256()) == 64
    with pytest.raises((FrozenInstanceError, AttributeError)):
        op.evidence_authority = True


def test_registry_is_strict_and_executes_plan():
    registry = ReasoningOperatorRegistry()
    op = _simple_operator()
    registry.register(op, lambda state, params: state + int(params.get("by", 1)))

    result = registry.execute_plan(
        1,
        [
            ReasoningStep("test.increment", {"by": 2}),
            ReasoningStep("test.increment", {"by": 3}),
        ],
    )
    assert result.final_state == 6
    assert result.steps_executed == ("test.increment", "test.increment")
    assert result.evidence_authority is False

    with pytest.raises(DuplicateReasoningOperator):
        registry.register(op, lambda state, params: state)

    with pytest.raises(UnknownReasoningOperator):
        registry.execute("missing", 1)


def test_paired_intervention_metrics():
    good = evaluate_paired_intervention(
        baseline_expected=2,
        baseline_actual=2,
        intervention_expected=3,
        intervention_actual=3,
        load_bearing=True,
    )
    assert good.pair_correct is True
    assert good.flip_consistent is True
    assert good.evidence_authority is False

    irrelevant = evaluate_paired_intervention(
        baseline_expected=2,
        baseline_actual=2,
        intervention_expected=2,
        intervention_actual=2,
        load_bearing=False,
    )
    assert irrelevant.pair_correct is True
    assert irrelevant.flip_consistent is True


def test_symmetry_reduction_reports_real_state_collapse():
    states = [
        (3, 1, 2),
        (1, 3, 2),
        (2, 1, 3),
        (9, 8, 7),
    ]
    result = evaluate_symmetry_reduction(
        states,
        lambda value: tuple(sorted(value)),
    )
    assert result.raw_states == 4
    assert result.canonical_states == 2
    assert result.eliminated_states == 2
    assert result.reduction_fraction == 0.5
    assert result.idempotent is True
    assert result.evidence_authority is False


def test_exact_geometric_registry_wires_backend_without_reimplementing_math():
    registry = build_exact_geometric_registry(_FakeNative)
    ids = {item["operator_id"] for item in registry.descriptors()}

    assert "math.combinatorics.permutation.inverse" in ids
    assert (
        "math.combinatorics.group.canonical_coordinate_representative"
        in ids
    )
    assert "math.exterior.wedge" in ids
    assert "math.geometry.simplex.barycentric" in ids
    assert all(
        item["evidence_authority"] is False
        for item in registry.descriptors()
    )

    swap = _FakePermutation((1, 0, 2))
    assert registry.execute(
        "math.combinatorics.permutation.act_coordinates",
        (10, 20, 30),
        {"permutation": swap},
    ) == (20, 10, 30)

    assert registry.execute(
        "math.combinatorics.group.canonical_coordinate_representative",
        (3, 1, 2),
        {"group": _FakeGroup()},
    ) == (1, 2, 3)


def test_exact_geometric_registry_fails_closed_for_missing_backend_surface():
    class Incomplete:
        ExactPermutation = _FakePermutation

    with pytest.raises(NativeReasoningBackendUnavailable):
        build_exact_geometric_registry(Incomplete)


@pytest.mark.parametrize(
    "operator_id",
    ["", "UPPER.case", "contains space"],
)
def test_invalid_operator_ids_rejected(operator_id):
    with pytest.raises(ValueError):
        ReasoningOperator(
            operator_id=operator_id,
            version="1",
            title="Bad",
            input_types=("x",),
            output_type="x",
            implementation_ref="test",
        )
