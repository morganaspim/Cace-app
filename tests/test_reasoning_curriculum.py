from __future__ import annotations

from dataclasses import FrozenInstanceError

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
    generate_permutation_action_pair,
)


class _FakeRational(int):
    pass


class _FakeVector(tuple):
    def __new__(cls, values):
        return super().__new__(cls, values)


class _FakePermutation:
    def __init__(self, image):
        if sorted(image) != list(range(len(image))):
            raise ValueError("not a permutation")
        self.image = tuple(image)

    @classmethod
    def identity(cls, degree):
        return cls(list(range(degree)))

    def act_coordinates(self, vector):
        out = [None] * len(self.image)
        for source, target in enumerate(self.image):
            out[target] = vector[source]
        return _FakeVector(out)


class _FakeNative:
    ExactRational = _FakeRational
    ExactVector = _FakeVector
    ExactPermutation = _FakePermutation


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
    return registry


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

    baseline, intervention, metrics = evaluate_pair(_registry(), pair1)
    assert baseline.correct is True
    assert intervention.correct is True
    assert metrics.pair_correct is True
    assert metrics.flip_consistent is True
    assert metrics.evidence_authority is False


def test_pair_generator_rejects_too_small_degree():
    with pytest.raises(ValueError):
        generate_permutation_action_pair(_FakeNative, seed=1, degree=1)
