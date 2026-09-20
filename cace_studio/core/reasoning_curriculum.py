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


def _require_native_task_symbols(native_module: Any, required: Sequence[str]) -> None:
    missing = [name for name in required if not hasattr(native_module, name)]
    if missing:
        raise ValueError("native task backend missing: " + ", ".join(missing))


def _single_step_pair(
    *,
    family: str,
    seed: int,
    generator_version: str,
    initial_state: Any,
    baseline_step: ReasoningStep,
    intervention_step: ReasoningStep,
    baseline_expected: Any,
    intervention_expected: Any,
) -> PairedReasoningTasks:
    pair_id = _stable_pair_id(family, seed, generator_version)
    split = composition_split((intervention_step,))
    load_bearing = baseline_expected != intervention_expected
    return PairedReasoningTasks(
        baseline=ReasoningTask(
            task_id=pair_id + ":baseline",
            family=family,
            seed=seed,
            generator_version=generator_version,
            split=split,
            initial_state=initial_state,
            steps=(baseline_step,),
            expected_output=baseline_expected,
            pair_id=pair_id,
            load_bearing_intervention=False,
        ),
        intervention=ReasoningTask(
            task_id=pair_id + ":intervention",
            family=family,
            seed=seed,
            generator_version=generator_version,
            split=split,
            initial_state=initial_state,
            steps=(intervention_step,),
            expected_output=intervention_expected,
            pair_id=pair_id,
            load_bearing_intervention=load_bearing,
        ),
    )


def generate_group_canonicalization_pair(
    native_module: Any,
    *,
    seed: int,
    degree: int = 3,
    max_elements: int = 128,
    generator_version: str = "cace-group-canonicalization-pair-v1",
) -> PairedReasoningTasks:
    """Generate a pair where a finite-group action changes the canonical state.

    Python chooses a deterministic exact vector and one transposition generator.
    The canonical representatives themselves are computed by the native
    FinitePermutationGroup implementation.
    """

    if degree < 2:
        raise ValueError("degree must be >= 2")
    if max_elements < 2:
        raise ValueError("max_elements must be >= 2")

    _require_native_task_symbols(
        native_module,
        (
            "ExactPermutation",
            "FinitePermutationGroup",
            "ExactVector",
            "ExactRational",
        ),
    )

    rng = random.Random(seed)
    vector = None
    generator = None

    # Find a seeded vector/transposition for which the native canonical text
    # strictly decreases. This guarantees the intervention is load-bearing
    # without reimplementing group canonicalization in Python.
    values = list(range(1, degree + 1))
    for _ in range(32):
        rng.shuffle(values)
        candidate_vector = native_module.ExactVector(
            [native_module.ExactRational(value) for value in values]
        )
        source_text = candidate_vector.canonical_text()
        candidates: list[Any] = []
        for i in range(degree):
            for j in range(i + 1, degree):
                image = list(range(degree))
                image[i], image[j] = image[j], image[i]
                permutation = native_module.ExactPermutation(image)
                moved = permutation.act_coordinates(candidate_vector)
                if moved.canonical_text() < source_text:
                    candidates.append(permutation)
        if candidates:
            vector = candidate_vector
            generator = candidates[rng.randrange(len(candidates))]
            break

    if vector is None or generator is None:
        # Deterministic fail-closed fallback for pathological RNG sequences.
        values = list(range(degree, 0, -1))
        vector = native_module.ExactVector(
            [native_module.ExactRational(value) for value in values]
        )
        image = list(range(degree))
        image[0], image[-1] = image[-1], image[0]
        generator = native_module.ExactPermutation(image)

    baseline_group = native_module.FinitePermutationGroup(
        degree,
        [],
        max_elements,
    )
    intervention_group = native_module.FinitePermutationGroup(
        degree,
        [generator],
        max_elements,
    )

    operator_id = "math.combinatorics.group.canonical_coordinate_representative"
    baseline_step = ReasoningStep(operator_id, {"group": baseline_group})
    intervention_step = ReasoningStep(operator_id, {"group": intervention_group})
    baseline_expected = baseline_group.canonical_coordinate_representative(vector)
    intervention_expected = intervention_group.canonical_coordinate_representative(vector)
    if baseline_expected == intervention_expected:
        raise RuntimeError("generated group intervention was not load-bearing")

    return _single_step_pair(
        family="finite-group-coordinate-canonicalization",
        seed=seed,
        generator_version=generator_version,
        initial_state=vector,
        baseline_step=baseline_step,
        intervention_step=intervention_step,
        baseline_expected=baseline_expected,
        intervention_expected=intervention_expected,
    )


def generate_exterior_wedge_pair(
    native_module: Any,
    *,
    seed: int,
    dimension: int = 3,
    generator_version: str = "cace-exterior-wedge-pair-v1",
) -> PairedReasoningTasks:
    """Generate an exact wedge pair: repeated basis vector vs distinct vector."""

    if dimension < 2:
        raise ValueError("dimension must be >= 2")
    _require_native_task_symbols(native_module, ("ExactExterior",))

    rng = random.Random(seed)
    first = rng.randrange(dimension)
    second = rng.randrange(dimension - 1)
    if second >= first:
        second += 1

    state = native_module.ExactExterior.basis_vector(dimension, first)
    same = native_module.ExactExterior.basis_vector(dimension, first)
    distinct = native_module.ExactExterior.basis_vector(dimension, second)

    operator_id = "math.exterior.wedge"
    baseline_step = ReasoningStep(operator_id, {"rhs": same})
    intervention_step = ReasoningStep(operator_id, {"rhs": distinct})
    baseline_expected = state.wedge(same)
    intervention_expected = state.wedge(distinct)
    if baseline_expected == intervention_expected:
        raise RuntimeError("generated exterior intervention was not load-bearing")

    return _single_step_pair(
        family="exterior-wedge-basis-intervention",
        seed=seed,
        generator_version=generator_version,
        initial_state=state,
        baseline_step=baseline_step,
        intervention_step=intervention_step,
        baseline_expected=baseline_expected,
        intervention_expected=intervention_expected,
    )


def generate_affine_apply_pair(
    native_module: Any,
    *,
    seed: int,
    dimension: int = 2,
    generator_version: str = "cace-affine-apply-pair-v1",
) -> PairedReasoningTasks:
    """Generate identity-vs-translation exact affine application tasks."""

    if dimension < 1:
        raise ValueError("dimension must be >= 1")
    _require_native_task_symbols(
        native_module,
        ("ExactRational", "ExactVector", "ExactMatrix", "ExactAffineMap"),
    )

    rng = random.Random(seed)
    point = native_module.ExactVector(
        [native_module.ExactRational(rng.randint(-4, 4)) for _ in range(dimension)]
    )

    translation_values = [rng.randint(-3, 3) for _ in range(dimension)]
    if all(value == 0 for value in translation_values):
        translation_values[seed % dimension] = 1
    translation = native_module.ExactVector(
        [native_module.ExactRational(value) for value in translation_values]
    )

    baseline_affine = native_module.ExactAffineMap.identity(dimension)
    intervention_affine = native_module.ExactAffineMap(
        native_module.ExactMatrix.identity(dimension),
        translation,
    )

    operator_id = "math.geometry.affine.apply"
    baseline_step = ReasoningStep(operator_id, {"affine": baseline_affine})
    intervention_step = ReasoningStep(operator_id, {"affine": intervention_affine})
    baseline_expected = baseline_affine.apply(point)
    intervention_expected = intervention_affine.apply(point)
    if baseline_expected == intervention_expected:
        raise RuntimeError("generated affine intervention was not load-bearing")

    return _single_step_pair(
        family="affine-translation-intervention",
        seed=seed,
        generator_version=generator_version,
        initial_state=point,
        baseline_step=baseline_step,
        intervention_step=intervention_step,
        baseline_expected=baseline_expected,
        intervention_expected=intervention_expected,
    )


def generate_simplex_barycentric_pair(
    native_module: Any,
    *,
    seed: int,
    dimension: int = 2,
    generator_version: str = "cace-simplex-barycentric-pair-v1",
) -> PairedReasoningTasks:
    """Generate a vertex-relabel intervention for exact simplex barycentrics."""

    if dimension < 2:
        raise ValueError("dimension must be >= 2")
    _require_native_task_symbols(
        native_module,
        ("ExactRational", "ExactVector", "ExactSimplex"),
    )

    zero = native_module.ExactRational(0)
    one = native_module.ExactRational(1)
    half = native_module.ExactRational(1, 2)

    origin = native_module.ExactVector([zero for _ in range(dimension)])
    basis_vertices = []
    for axis in range(dimension):
        coords = [zero for _ in range(dimension)]
        coords[axis] = one
        basis_vertices.append(native_module.ExactVector(coords))

    baseline_vertices = [origin, *basis_vertices]
    baseline_simplex = native_module.ExactSimplex(baseline_vertices)

    rng = random.Random(seed)
    left = rng.randrange(dimension)
    right = rng.randrange(dimension - 1)
    if right >= left:
        right += 1
    intervention_basis = list(basis_vertices)
    intervention_basis[left], intervention_basis[right] = (
        intervention_basis[right],
        intervention_basis[left],
    )
    intervention_simplex = native_module.ExactSimplex([origin, *intervention_basis])

    point_coords = [zero for _ in range(dimension)]
    point_coords[left] = half
    point = native_module.ExactVector(point_coords)

    operator_id = "math.geometry.simplex.barycentric"
    baseline_step = ReasoningStep(operator_id, {"simplex": baseline_simplex})
    intervention_step = ReasoningStep(
        operator_id,
        {"simplex": intervention_simplex},
    )
    baseline_expected = baseline_simplex.barycentric_coordinates(point)
    intervention_expected = intervention_simplex.barycentric_coordinates(point)
    if baseline_expected == intervention_expected:
        raise RuntimeError("generated simplex intervention was not load-bearing")

    return _single_step_pair(
        family="simplex-vertex-relabel-barycentric",
        seed=seed,
        generator_version=generator_version,
        initial_state=point,
        baseline_step=baseline_step,
        intervention_step=intervention_step,
        baseline_expected=baseline_expected,
        intervention_expected=intervention_expected,
    )


@dataclass(frozen=True)
class ReasoningCurriculumBatch:
    batch_id: str
    seed: int
    train_pairs: tuple[PairedReasoningTasks, ...]
    holdout_pairs: tuple[PairedReasoningTasks, ...]
    holdout_family: str
    evidence_authority: bool = field(default=False, init=False)

    @property
    def pair_count(self) -> int:
        return len(self.train_pairs) + len(self.holdout_pairs)

    @property
    def task_count(self) -> int:
        return 2 * self.pair_count


@dataclass(frozen=True)
class CurriculumAttentionSignal:
    skill_id: str
    node_ids: tuple[str, ...]
    score: float
    reasons: tuple[str, ...]
    evidence_authority: bool = field(default=False, init=False)


_EXACT_FAMILY_GENERATORS = (
    ("permutation-coordinate-action", generate_permutation_action_pair),
    ("finite-group-coordinate-canonicalization", generate_group_canonicalization_pair),
    ("exterior-wedge-basis-intervention", generate_exterior_wedge_pair),
    ("affine-translation-intervention", generate_affine_apply_pair),
    ("simplex-vertex-relabel-barycentric", generate_simplex_barycentric_pair),
)


def _derived_seed(seed: int, label: str) -> int:
    raw = f"{seed}|{label}".encode("utf-8")
    return int(sha256(raw).hexdigest()[:16], 16) % (2**31)


def generate_exact_curriculum_batch(
    native_module: Any,
    *,
    seed: int,
    holdout_family: str | None = None,
) -> ReasoningCurriculumBatch:
    """Generate one seeded pair from each exact ReasoningOperator family.

    One entire family is held out so evaluation can measure transfer across a
    generator family rather than merely unseen values from a trained family.
    """

    families = tuple(name for name, _ in _EXACT_FAMILY_GENERATORS)
    if holdout_family is None:
        index = _derived_seed(seed, "family-holdout") % len(families)
        holdout_family = families[index]
    if holdout_family not in families:
        raise ValueError(f"unknown holdout_family: {holdout_family}")

    train: list[PairedReasoningTasks] = []
    holdout: list[PairedReasoningTasks] = []
    for family, generator in _EXACT_FAMILY_GENERATORS:
        pair = generator(
            native_module,
            seed=_derived_seed(seed, family),
        )
        if family == holdout_family:
            holdout.append(pair)
        else:
            train.append(pair)

    batch_id = sha256(
        f"exact-curriculum-v1|{seed}|{holdout_family}".encode("utf-8")
    ).hexdigest()
    return ReasoningCurriculumBatch(
        batch_id=batch_id,
        seed=seed,
        train_pairs=tuple(train),
        holdout_pairs=tuple(holdout),
        holdout_family=holdout_family,
    )


_HEARTBEAT_PRIORITY = {
    "FAILED": 1.00,
    "BLOCKED": 0.95,
    "STALE": 0.85,
    "RESEARCH_INTEREST": 0.65,
    "WAITING": 0.45,
    "ACTIVE": 0.35,
    "READY": 0.25,
    "VERIFYING": 0.20,
    "VERIFIED": 0.05,
    "DORMANT": 0.00,
}


def curriculum_signals_from_perception(
    packet: Mapping[str, Any],
    *,
    node_skill_ids: Mapping[str, Sequence[str]],
) -> tuple[CurriculumAttentionSignal, ...]:
    """Convert a validated Agent Perception Packet into advisory skill signals.

    The JSON schema remains the authoritative packet validator. This adapter
    rechecks the fields it consumes and the non-evidence boundary so malformed
    or authority-bearing packets fail closed.
    """

    if packet.get("schema_version") != "cace-agent-perception-v1":
        raise ValueError("unsupported agent perception schema")
    if packet.get("evidence_authority") is not False:
        raise ValueError("agent perception must have evidence_authority=false")
    nodes = packet.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("agent perception nodes must be an array")

    aggregated: dict[str, dict[str, Any]] = {}
    for raw in nodes:
        if not isinstance(raw, Mapping):
            raise ValueError("agent perception node must be an object")
        node_id = raw.get("node_id")
        heartbeat = raw.get("heartbeat_state")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("agent perception node_id must be non-empty")
        if heartbeat not in _HEARTBEAT_PRIORITY:
            raise ValueError(f"unsupported heartbeat_state: {heartbeat}")

        skills = tuple(node_skill_ids.get(node_id, ()))
        if not skills:
            continue

        reasons: list[str] = [f"heartbeat:{heartbeat}"]
        score = _HEARTBEAT_PRIORITY[heartbeat]

        if raw.get("changed") is True:
            score += 0.15
            reasons.append("semantic-change")

        trend = raw.get("residual_trend")
        if trend == "WORSENING":
            score += 0.20
            reasons.append("residual-worsening")
        elif trend not in {"IMPROVING", "STABLE", "UNKNOWN"}:
            raise ValueError(f"unsupported residual_trend: {trend}")

        canonical = raw.get("canonical_evidence_state")
        if canonical == "FAIL":
            score += 0.20
            reasons.append("canonical-fail-mirrored")
        elif canonical == "STALE":
            score += 0.15
            reasons.append("canonical-stale-mirrored")
        elif canonical == "NOT_RUN":
            score += 0.05
            reasons.append("canonical-not-run-mirrored")
        elif canonical not in {"PASS", "UNKNOWN"}:
            raise ValueError(f"unsupported canonical_evidence_state: {canonical}")

        research_interest = raw.get("research_interest")
        resource_pressure = raw.get("resource_pressure")
        if not isinstance(research_interest, (int, float)) or not 0 <= research_interest <= 1:
            raise ValueError("research_interest must be in [0,1]")
        if not isinstance(resource_pressure, (int, float)) or not 0 <= resource_pressure <= 1:
            raise ValueError("resource_pressure must be in [0,1]")

        if research_interest:
            score += 0.20 * float(research_interest)
            reasons.append("research-interest")
        if resource_pressure:
            # High resource pressure reduces immediate lesson priority rather
            # than being interpreted as scientific difficulty or evidence.
            score -= 0.15 * float(resource_pressure)
            reasons.append("resource-pressure")

        score = max(0.0, min(1.5, score))
        for skill_id in skills:
            if not skill_id:
                raise ValueError("skill IDs must be non-empty")
            entry = aggregated.setdefault(
                skill_id,
                {"score": 0.0, "nodes": set(), "reasons": set()},
            )
            entry["score"] = max(float(entry["score"]), score)
            entry["nodes"].add(node_id)
            entry["reasons"].update(reasons)

    return tuple(
        CurriculumAttentionSignal(
            skill_id=skill_id,
            node_ids=tuple(sorted(value["nodes"])),
            score=float(value["score"]),
            reasons=tuple(sorted(value["reasons"])),
        )
        for skill_id, value in sorted(aggregated.items())
    )


def rank_heartbeat_aware_skills(
    mastery: MasteryTable,
    candidate_skill_ids: Sequence[str],
    *,
    signals: Sequence[CurriculumAttentionSignal] = (),
    target_accuracy: float = 0.75,
) -> tuple[str, ...]:
    """Rank curriculum skills using perception urgency, then mastery frontier."""

    if not candidate_skill_ids:
        raise ValueError("candidate_skill_ids must be non-empty")
    if not 0.0 <= target_accuracy <= 1.0:
        raise ValueError("target_accuracy must be in [0,1]")

    signal_score = {signal.skill_id: signal.score for signal in signals}

    def key(skill_id: str) -> tuple[float, int, float, int, str]:
        skill = mastery.get(skill_id)
        unseen = 0 if skill.attempts == 0 else 1
        distance = abs(skill.accuracy - target_accuracy)
        return (
            -signal_score.get(skill_id, 0.0),
            unseen,
            distance,
            skill.attempts,
            skill_id,
        )

    return tuple(sorted(candidate_skill_ids, key=key))


def curriculum_batch_manifest(batch: ReasoningCurriculumBatch) -> dict[str, Any]:
    """Return a JSON-safe deterministic replay manifest for a curriculum batch.

    Native state/parameter objects are intentionally not serialized here. Replay
    regenerates them from family, seed, generator version, and the canonical
    native backend.
    """

    def pair_record(pair: PairedReasoningTasks, *, role: str) -> dict[str, Any]:
        return {
            "role": role,
            "family": pair.baseline.family,
            "pair_id": pair.baseline.pair_id,
            "seed": pair.baseline.seed,
            "generator_version": pair.baseline.generator_version,
            "split": pair.baseline.split,
            "baseline_task_id": pair.baseline.task_id,
            "intervention_task_id": pair.intervention.task_id,
            "baseline_operator_signature": list(pair.baseline.operator_signature()),
            "intervention_operator_signature": list(
                pair.intervention.operator_signature()
            ),
            "load_bearing_intervention": pair.intervention.load_bearing_intervention,
            "evidence_authority": False,
        }

    records = [
        *(pair_record(pair, role="train") for pair in batch.train_pairs),
        *(pair_record(pair, role="holdout") for pair in batch.holdout_pairs),
    ]
    records.sort(key=lambda item: (item["role"], item["family"], item["pair_id"]))
    return {
        "schema_version": "cace-reasoning-curriculum-batch-v1",
        "batch_id": batch.batch_id,
        "seed": batch.seed,
        "holdout_family": batch.holdout_family,
        "pair_count": batch.pair_count,
        "task_count": batch.task_count,
        "pairs": records,
        "replay_rule": (
            "regenerate exact native task objects from family + seed + "
            "generator_version; manifest carries no mathematical evidence"
        ),
        "evidence_authority": False,
    }


def curriculum_batch_manifest_sha256(batch: ReasoningCurriculumBatch) -> str:
    import json

    payload = json.dumps(
        curriculum_batch_manifest(batch),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def replay_exact_curriculum_batch(
    native_module: Any,
    manifest: Mapping[str, Any],
) -> ReasoningCurriculumBatch:
    """Replay a batch from deterministic manifest identity fields."""

    if manifest.get("schema_version") != "cace-reasoning-curriculum-batch-v1":
        raise ValueError("unsupported curriculum batch manifest")
    if manifest.get("evidence_authority") is not False:
        raise ValueError("curriculum manifest must have evidence_authority=false")

    seed = manifest.get("seed")
    holdout_family = manifest.get("holdout_family")
    batch_id = manifest.get("batch_id")
    if not isinstance(seed, int):
        raise ValueError("curriculum manifest seed must be an integer")
    if not isinstance(holdout_family, str) or not holdout_family:
        raise ValueError("curriculum manifest holdout_family must be non-empty")
    if not isinstance(batch_id, str) or len(batch_id) != 64:
        raise ValueError("curriculum manifest batch_id must be a SHA-256 string")

    replayed = generate_exact_curriculum_batch(
        native_module,
        seed=seed,
        holdout_family=holdout_family,
    )
    if replayed.batch_id != batch_id:
        raise ValueError("curriculum manifest batch identity mismatch")

    expected = curriculum_batch_manifest(replayed)
    supplied_pairs = manifest.get("pairs")
    if supplied_pairs != expected["pairs"]:
        raise ValueError("curriculum manifest pair metadata mismatch")
    if manifest.get("pair_count") != expected["pair_count"]:
        raise ValueError("curriculum manifest pair_count mismatch")
    if manifest.get("task_count") != expected["task_count"]:
        raise ValueError("curriculum manifest task_count mismatch")
    return replayed


def curriculum_symmetry_benchmark_record(
    *,
    raw_states: int,
    canonical_states: int,
    eliminated_states: int,
    reduction_fraction: float,
    canonicalization_idempotent: bool,
    raw_key_seconds: float | None = None,
    canonicalization_seconds: float | None = None,
) -> dict[str, Any]:
    """Normalize measured group-reasoning metrics for curriculum reporting."""

    if raw_states < 0 or canonical_states < 0 or eliminated_states < 0:
        raise ValueError("symmetry benchmark counts must be non-negative")
    if canonical_states > raw_states:
        raise ValueError("canonical_states cannot exceed raw_states")
    if eliminated_states != raw_states - canonical_states:
        raise ValueError("eliminated_states must equal raw_states-canonical_states")
    if not 0.0 <= reduction_fraction <= 1.0:
        raise ValueError("reduction_fraction must be in [0,1]")

    return {
        "schema_version": "cace-curriculum-symmetry-benchmark-v1",
        "raw_states": raw_states,
        "canonical_states": canonical_states,
        "eliminated_states": eliminated_states,
        "reduction_fraction": reduction_fraction,
        "canonicalization_idempotent": bool(canonicalization_idempotent),
        "raw_key_seconds": raw_key_seconds,
        "canonicalization_seconds": canonicalization_seconds,
        "performance_claim": "none; timings are descriptive only",
        "evidence_authority": False,
    }
