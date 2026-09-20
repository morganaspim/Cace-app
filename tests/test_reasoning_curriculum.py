from __future__ import annotations

from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from cace_studio.core.reasoning import (
    ReasoningOperator,
    ReasoningOperatorRegistry,
)
from cace_studio.core.reasoning_curriculum import (
    MasteryTable,
    ReasoningStep,
    ReasoningTask,
    composition_signature,
    composition_split,
    evaluate_pair,
    evaluate_task,
    generate_affine_apply_pair,
    generate_exterior_wedge_pair,
    generate_group_canonicalization_pair,
    generate_permutation_action_pair,
    generate_simplex_barycentric_pair,
)


_FakeRational = Fraction


class _FakeVector(tuple):
    def __new__(cls, values):
        return super().__new__(cls, values)

    def canonical_text(self):
        return "[" + ",".join(str(value) for value in self) + "]"


class _FakePermutation:
    def __init__(self, image):
        if sorted(image) != list(range(len(image))):
            raise ValueError("not a permutation")
        self.image = tuple(image)

    @classmethod
    def identity(cls, degree):
        return cls(list(range(degree)))

    def inverse(self):
        out = [0] * len(self.image)
        for source, target in enumerate(self.image):
            out[target] = source
        return type(self)(out)

    def compose(self, inner):
        return type(self)(
            [self.image[inner.image[index]] for index in range(len(self.image))]
        )

    def act_coordinates(self, vector):
        out = [None] * len(self.image)
        for source, target in enumerate(self.image):
            out[target] = vector[source]
        return _FakeVector(out)


class _FakeGroup:
    def __init__(self, degree, generators, max_elements=4096):
        self.degree = degree
        self.generators = tuple(generators)
        seen = {tuple(range(degree))}
        queue = [_FakePermutation.identity(degree)]
        moves = [*self.generators, *(item.inverse() for item in self.generators)]
        for current in queue:
            for move in moves:
                nxt = move.compose(current)
                if nxt.image not in seen:
                    seen.add(nxt.image)
                    queue.append(nxt)
                    if len(queue) > max_elements:
                        raise ValueError("group too large")
        self.elements = tuple(queue)

    def canonical_coordinate_representative(self, values):
        candidates = [item.act_coordinates(values) for item in self.elements]
        return min(candidates, key=lambda value: value.canonical_text())


class _FakeExterior:
    def __init__(self, dimension, terms=None):
        self.dimension = dimension
        self.terms = {
            int(mask): Fraction(value)
            for mask, value in (terms or {}).items()
            if Fraction(value) != 0
        }

    @classmethod
    def basis_vector(cls, dimension, index):
        return cls(dimension, {1 << index: Fraction(1)})

    @staticmethod
    def _wedge_sign(a, b):
        parity = 0
        while a:
            i = (a & -a).bit_length() - 1
            lower = (1 << i) - 1
            parity ^= (b & lower).bit_count() & 1
            a &= a - 1
        return 1 if parity == 0 else -1

    def wedge(self, rhs):
        if self.dimension != rhs.dimension:
            raise ValueError("dimension mismatch")
        out = {}
        for a, ca in self.terms.items():
            for b, cb in rhs.terms.items():
                if a & b:
                    continue
                mask = a | b
                value = Fraction(self._wedge_sign(a, b)) * ca * cb
                out[mask] = out.get(mask, Fraction(0)) + value
                if out[mask] == 0:
                    del out[mask]
        return type(self)(self.dimension, out)

    def __eq__(self, other):
        return (
            isinstance(other, _FakeExterior)
            and self.dimension == other.dimension
            and self.terms == other.terms
        )


class _FakeMatrix:
    def __init__(self, rows):
        self.rows = tuple(tuple(Fraction(value) for value in row) for row in rows)

    @classmethod
    def identity(cls, dimension):
        return cls(
            [
                [Fraction(int(row == col)) for col in range(dimension)]
                for row in range(dimension)
            ]
        )

    def matvec(self, vector):
        return _FakeVector(
            sum((value * vector[col] for col, value in enumerate(row)), Fraction(0))
            for row in self.rows
        )


class _FakeAffine:
    def __init__(self, linear, translation):
        self.linear = linear
        self.translation = _FakeVector(translation)

    @classmethod
    def identity(cls, dimension):
        return cls(_FakeMatrix.identity(dimension), _FakeVector([0] * dimension))

    def apply(self, point):
        linear = self.linear.matvec(point)
        return _FakeVector(
            linear[index] + self.translation[index]
            for index in range(len(linear))
        )


class _FakeSimplex:
    def __init__(self, vertices):
        self.vertices = tuple(_FakeVector(vertex) for vertex in vertices)

    def barycentric_coordinates(self, point):
        dimension = len(point)
        lambdas = [Fraction(1) - sum(point, Fraction(0))]
        for vertex in self.vertices[1:]:
            axes = [index for index, value in enumerate(vertex) if value == 1]
            if len(axes) != 1:
                raise ValueError("fake simplex only supports permuted standard basis")
            lambdas.append(point[axes[0]])
        if len(lambdas) != dimension + 1:
            raise ValueError("invalid simplex")
        return _FakeVector(lambdas)


class _FakeNative:
    ExactRational = _FakeRational
    ExactVector = _FakeVector
    ExactPermutation = _FakePermutation
    FinitePermutationGroup = _FakeGroup
    ExactExterior = _FakeExterior
    ExactMatrix = _FakeMatrix
    ExactAffineMap = _FakeAffine
    ExactSimplex = _FakeSimplex


def _registry():
    registry = ReasoningOperatorRegistry()
    registry.register(
        ReasoningOperator(
            operator_id="test.add",
            version="1",
            title="Add",
            input_types=("integer", "integer"),
            output_type="integer",
            implementation_ref="test",
            cost_class="constant",
        ),
        lambda state, params: state + params["value"],
    )
    registry.register(
        ReasoningOperator(
            operator_id="math.combinatorics.permutation.act_coordinates",
            version="1",
            title="Act",
            input_types=("ExactVector", "ExactPermutation"),
            output_type="ExactVector",
            implementation_ref="test",
            cost_class="linear",
        ),
        lambda state, params: params["permutation"].act_coordinates(state),
    )
    registry.register(
        ReasoningOperator(
            operator_id="math.combinatorics.group.canonical_coordinate_representative",
            version="1",
            title="Canonicalize",
            input_types=("ExactVector", "FinitePermutationGroup"),
            output_type="ExactVector",
            implementation_ref="test",
            cost_class="bounded-enumeration",
        ),
        lambda state, params: params["group"].canonical_coordinate_representative(state),
    )
    registry.register(
        ReasoningOperator(
            operator_id="math.exterior.wedge",
            version="1",
            title="Wedge",
            input_types=("ExactExterior", "ExactExterior"),
            output_type="ExactExterior",
            implementation_ref="test",
            cost_class="quadratic",
        ),
        lambda state, params: state.wedge(params["rhs"]),
    )
    registry.register(
        ReasoningOperator(
            operator_id="math.geometry.affine.apply",
            version="1",
            title="Affine",
            input_types=("ExactVector", "ExactAffineMap"),
            output_type="ExactVector",
            implementation_ref="test",
            cost_class="quadratic",
        ),
        lambda state, params: params["affine"].apply(state),
    )
    registry.register(
        ReasoningOperator(
            operator_id="math.geometry.simplex.barycentric",
            version="1",
            title="Barycentric",
            input_types=("ExactVector", "ExactSimplex"),
            output_type="ExactVector",
            implementation_ref="test",
            cost_class="cubic",
        ),
        lambda state, params: params["simplex"].barycentric_coordinates(state),
    )
    return registry


def _assert_good_pair(pair):
    baseline, intervention, metrics = evaluate_pair(_registry(), pair)
    assert baseline.correct is True
    assert intervention.correct is True
    assert metrics.pair_correct is True
    assert metrics.flip_consistent is True
    assert metrics.evidence_authority is False
    assert pair.evidence_authority is False


def test_task_evaluation_and_no_evidence_authority():
    task = ReasoningTask(
        task_id="t1",
        family="arithmetic",
        seed=1,
        generator_version="v1",
        split="train",
        initial_state=2,
        steps=(ReasoningStep("test.add", {"value": 3}),),
        expected_output=5,
    )
    outcome, plan = evaluate_task(_registry(), task)
    assert outcome.correct is True
    assert outcome.plan_valid is True
    assert plan is not None
    assert outcome.evidence_authority is False
    with pytest.raises((FrozenInstanceError, AttributeError)):
        task.evidence_authority = True


def test_invalid_plan_is_recorded_without_evidence_promotion():
    task = ReasoningTask(
        task_id="bad",
        family="arithmetic",
        seed=1,
        generator_version="v1",
        split="train",
        initial_state=2,
        steps=(ReasoningStep("missing.operator"),),
        expected_output=2,
    )
    outcome, plan = evaluate_task(_registry(), task)
    assert outcome.correct is False
    assert outcome.plan_valid is False
    assert plan is None
    assert outcome.evidence_authority is False


def test_composition_holdout_split_is_deterministic_by_operator_sequence():
    steps_a = (
        ReasoningStep("test.add", {"value": 1}),
        ReasoningStep("test.add", {"value": 2}),
    )
    steps_b = (
        ReasoningStep("test.add", {"value": 999}),
        ReasoningStep("test.add", {"value": -100}),
    )
    assert composition_signature(steps_a) == composition_signature(steps_b)
    assert composition_split(steps_a) == composition_split(steps_b)


def test_mastery_table_tracks_frontier_and_transfer():
    table = MasteryTable()
    assert table.select_frontier(["a", "b"]) == "a"

    table.record(["a"], correct=True)
    table.record(["a"], correct=True, paired_consistent=True, transfer=True)
    table.record(["a"], correct=False, paired_consistent=False, transfer=True)

    skill = table.get("a")
    assert skill.attempts == 3
    assert skill.correct == 2
    assert skill.accuracy == pytest.approx(2 / 3)
    assert skill.pair_consistency == pytest.approx(0.5)
    assert skill.transfer_accuracy == pytest.approx(0.5)
    assert skill.evidence_authority is False

    snapshot = table.snapshot()
    assert snapshot[0]["evidence_authority"] is False


def test_permutation_pair_generator_is_seeded_and_exact_backend_driven():
    pair1 = generate_permutation_action_pair(_FakeNative, seed=123)
    pair2 = generate_permutation_action_pair(_FakeNative, seed=123)

    assert pair1.baseline.task_id == pair2.baseline.task_id
    assert pair1.baseline.initial_state == pair2.baseline.initial_state
    assert pair1.intervention.expected_output == pair2.intervention.expected_output
    assert pair1.intervention.load_bearing_intervention is True
    _assert_good_pair(pair1)


def test_group_canonicalization_pair_is_seeded_and_load_bearing():
    pair1 = generate_group_canonicalization_pair(_FakeNative, seed=44)
    pair2 = generate_group_canonicalization_pair(_FakeNative, seed=44)
    assert pair1.baseline.task_id == pair2.baseline.task_id
    assert pair1.baseline.initial_state == pair2.baseline.initial_state
    assert pair1.baseline.expected_output != pair1.intervention.expected_output
    assert pair1.intervention.load_bearing_intervention is True
    _assert_good_pair(pair1)


def test_exterior_wedge_pair_distinguishes_nilpotent_and_distinct_basis_wedge():
    pair = generate_exterior_wedge_pair(_FakeNative, seed=9)
    assert pair.baseline.expected_output != pair.intervention.expected_output
    assert pair.intervention.load_bearing_intervention is True
    _assert_good_pair(pair)


def test_affine_pair_uses_exact_identity_vs_translation():
    pair1 = generate_affine_apply_pair(_FakeNative, seed=71)
    pair2 = generate_affine_apply_pair(_FakeNative, seed=71)
    assert pair1.baseline.initial_state == pair2.baseline.initial_state
    assert pair1.intervention.expected_output == pair2.intervention.expected_output
    assert pair1.baseline.expected_output != pair1.intervention.expected_output
    _assert_good_pair(pair1)


def test_simplex_pair_tracks_vertex_relabel_in_barycentric_coordinates():
    pair = generate_simplex_barycentric_pair(_FakeNative, seed=17)
    assert pair.baseline.expected_output != pair.intervention.expected_output
    assert pair.intervention.load_bearing_intervention is True
    _assert_good_pair(pair)


@pytest.mark.parametrize(
    ("generator", "kwargs"),
    [
        (generate_permutation_action_pair, {"degree": 1}),
        (generate_group_canonicalization_pair, {"degree": 1}),
        (generate_exterior_wedge_pair, {"dimension": 1}),
        (generate_affine_apply_pair, {"dimension": 0}),
        (generate_simplex_barycentric_pair, {"dimension": 1}),
    ],
)
def test_generators_reject_invalid_dimensions(generator, kwargs):
    with pytest.raises(ValueError):
        generator(_FakeNative, seed=1, **kwargs)
