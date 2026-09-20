from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import random
from typing import Any, Iterable, Mapping, Sequence

from .reasoning import (
    PairedInterventionResult,
    ReasoningOperatorRegistry,
    ReasoningPlanResult,
    ReasoningStep,
    evaluate_paired_intervention,
)


@dataclass(frozen=True)
class ReasoningTask:
    task_id: str
    family: str
    seed: int
    generator_version: str
    split: str
    initial_state: Any
    steps: tuple[ReasoningStep, ...]
    expected_output: Any
    pair_id: str | None = None
    load_bearing_intervention: bool = False
    evidence_authority: bool = field(default=False, init=False)

    def operator_signature(self) -> tuple[str, ...]:
        return tuple(step.operator_id for step in self.steps)


@dataclass(frozen=True)
class ReasoningTaskOutcome:
    task_id: str
    correct: bool
    plan_valid: bool
    actual_output: Any
    expected_output: Any
    operator_signature: tuple[str, ...]
    evidence_authority: bool = field(default=False, init=False)


@dataclass(frozen=True)
class PairedReasoningTasks:
    baseline: ReasoningTask
    intervention: ReasoningTask
    evidence_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self.baseline.pair_id or self.baseline.pair_id != self.intervention.pair_id:
            raise ValueError("paired tasks must share a non-empty pair_id")


@dataclass
class SkillMastery:
    skill_id: str
    attempts: int = 0
    correct: int = 0
    paired_attempts: int = 0
    paired_consistent: int = 0
    transfer_attempts: int = 0
    transfer_correct: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts if self.attempts else 0.0

    @property
    def pair_consistency(self) -> float:
        return (
            self.paired_consistent / self.paired_attempts
            if self.paired_attempts
            else 0.0
        )

    @property
    def transfer_accuracy(self) -> float:
        return (
            self.transfer_correct / self.transfer_attempts
            if self.transfer_attempts
            else 0.0
        )

    @property
    def evidence_authority(self) -> bool:
        return False


class MasteryTable:
    def __init__(self) -> None:
        self._skills: dict[str, SkillMastery] = {}

    def get(self, skill_id: str) -> SkillMastery:
        if skill_id not in self._skills:
            self._skills[skill_id] = SkillMastery(skill_id=skill_id)
        return self._skills[skill_id]

    def record(
        self,
        skill_ids: Iterable[str],
        *,
        correct: bool,
        paired_consistent: bool | None = None,
        transfer: bool = False,
    ) -> None:
        for skill_id in skill_ids:
            skill = self.get(skill_id)
            skill.attempts += 1
            skill.correct += int(correct)
            if paired_consistent is not None:
                skill.paired_attempts += 1
                skill.paired_consistent += int(paired_consistent)
            if transfer:
                skill.transfer_attempts += 1
                skill.transfer_correct += int(correct)

    def snapshot(self) -> list[dict[str, Any]]:
        out = []
        for skill_id in sorted(self._skills):
            skill = self._skills[skill_id]
            out.append(
                {
                    "skill_id": skill.skill_id,
                    "attempts": skill.attempts,
                    "correct": skill.correct,
                    "accuracy": skill.accuracy,
                    "paired_attempts": skill.paired_attempts,
                    "paired_consistency": skill.pair_consistency,
                    "transfer_attempts": skill.transfer_attempts,
                    "transfer_accuracy": skill.transfer_accuracy,
                    "evidence_authority": False,
                }
            )
        return out

    def select_frontier(
        self,
        candidate_skill_ids: Sequence[str],
        *,
        target_accuracy: float = 0.75,
    ) -> str:
        if not candidate_skill_ids:
            raise ValueError("candidate_skill_ids must be non-empty")
        if not 0.0 <= target_accuracy <= 1.0:
            raise ValueError("target_accuracy must be in [0,1]")

        def priority(skill_id: str) -> tuple[int, float, int, str]:
            skill = self.get(skill_id)
            unseen = 0 if skill.attempts == 0 else 1
            distance = abs(skill.accuracy - target_accuracy)
            return (unseen, distance, skill.attempts, skill_id)

        return min(candidate_skill_ids, key=priority)


def composition_signature(steps: Sequence[ReasoningStep]) -> str:
    payload = "\n".join(step.operator_id for step in steps).encode("utf-8")
    return sha256(payload).hexdigest()


def composition_split(
    steps: Sequence[ReasoningStep],
    *,
    holdout_modulus: int = 5,
    holdout_bucket: int = 0,
) -> str:
    if holdout_modulus < 2:
        raise ValueError("holdout_modulus must be >= 2")
    if not 0 <= holdout_bucket < holdout_modulus:
        raise ValueError("holdout_bucket out of range")
    digest = composition_signature(steps)
    bucket = int(digest[:16], 16) % holdout_modulus
    return "holdout" if bucket == holdout_bucket else "train"


def evaluate_task(
    registry: ReasoningOperatorRegistry,
    task: ReasoningTask,
) -> tuple[ReasoningTaskOutcome, ReasoningPlanResult | None]:
    try:
        plan = registry.execute_plan(task.initial_state, task.steps)
    except Exception:
        return (
            ReasoningTaskOutcome(
                task_id=task.task_id,
                correct=False,
                plan_valid=False,
                actual_output=None,
                expected_output=task.expected_output,
                operator_signature=task.operator_signature(),
            ),
            None,
        )

    return (
        ReasoningTaskOutcome(
            task_id=task.task_id,
            correct=plan.final_state == task.expected_output,
            plan_valid=True,
            actual_output=plan.final_state,
            expected_output=task.expected_output,
            operator_signature=task.operator_signature(),
        ),
        plan,
    )


def evaluate_pair(
    registry: ReasoningOperatorRegistry,
    pair: PairedReasoningTasks,
) -> tuple[ReasoningTaskOutcome, ReasoningTaskOutcome, PairedInterventionResult]:
    baseline, _ = evaluate_task(registry, pair.baseline)
    intervention, _ = evaluate_task(registry, pair.intervention)
    metrics = evaluate_paired_intervention(
        baseline_expected=pair.baseline.expected_output,
        baseline_actual=baseline.actual_output,
        intervention_expected=pair.intervention.expected_output,
        intervention_actual=intervention.actual_output,
        load_bearing=pair.intervention.load_bearing_intervention,
    )
    return baseline, intervention, metrics


def _stable_pair_id(family: str, seed: int, version: str) -> str:
    raw = f"{family}|{seed}|{version}".encode("utf-8")
    return sha256(raw).hexdigest()


def generate_permutation_action_pair(
    native_module: Any,
    *,
    seed: int,
    degree: int = 3,
    generator_version: str = "cace-permutation-pair-v1",
) -> PairedReasoningTasks:
    """Generate a deterministic paired exact-permutation task.

    Python selects/relabels an example; expected mathematical outputs are
    produced by the canonical native ExactPermutation implementation.
    """

    if degree < 2:
        raise ValueError("degree must be >= 2")

    required = ("ExactPermutation", "ExactVector", "ExactRational")
    missing = [name for name in required if not hasattr(native_module, name)]
    if missing:
        raise ValueError("native task backend missing: " + ", ".join(missing))

    rng = random.Random(seed)

    values = list(range(1, degree + 1))
    rng.shuffle(values)
    vector = native_module.ExactVector(
        [native_module.ExactRational(value) for value in values]
    )

    identity = native_module.ExactPermutation.identity(degree)

    image = list(range(degree))
    while image == list(range(degree)):
        rng.shuffle(image)
    intervention_permutation = native_module.ExactPermutation(image)

    operator_id = "math.combinatorics.permutation.act_coordinates"
    baseline_step = ReasoningStep(
        operator_id,
        {"permutation": identity},
    )
    intervention_step = ReasoningStep(
        operator_id,
        {"permutation": intervention_permutation},
    )

    baseline_expected = identity.act_coordinates(vector)
    intervention_expected = intervention_permutation.act_coordinates(vector)
    pair_id = _stable_pair_id(
        "permutation-coordinate-action",
        seed,
        generator_version,
    )

    baseline_steps = (baseline_step,)
    intervention_steps = (intervention_step,)
    split = composition_split(intervention_steps)

    return PairedReasoningTasks(
        baseline=ReasoningTask(
            task_id=pair_id + ":baseline",
            family="permutation-coordinate-action",
            seed=seed,
            generator_version=generator_version,
            split=split,
            initial_state=vector,
            steps=baseline_steps,
            expected_output=baseline_expected,
            pair_id=pair_id,
            load_bearing_intervention=False,
        ),
        intervention=ReasoningTask(
            task_id=pair_id + ":intervention",
            family="permutation-coordinate-action",
            seed=seed,
            generator_version=generator_version,
            split=split,
            initial_state=vector,
            steps=intervention_steps,
            expected_output=intervention_expected,
            pair_id=pair_id,
            load_bearing_intervention=True,
        ),
    )
