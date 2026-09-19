from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose, isfinite
import random
from typing import Any, Callable, Iterable, Mapping, Sequence


State = Any
OperatorFn = Callable[[State, Mapping[str, Any]], State]


def _canonical_identifier(value: str, *, field_name: str) -> str:
    text = str(value)
    if not text or text != text.strip():
        raise ValueError(f"{field_name} must be a non-empty canonical string")
    if any(char.isspace() for char in text):
        raise ValueError(f"{field_name} must not contain whitespace")
    return text


def _state_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "str"
    if (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        return "point2"
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return "pair"
    if isinstance(value, Mapping):
        return "mapping"
    return "any"


def _matches_type(value: Any, type_name: str) -> bool:
    if type_name == "any":
        return True
    actual = _state_type(value)
    if type_name == "number":
        return actual in {"int", "number"}
    if type_name == "pair":
        return actual in {"pair", "point2"}
    return actual == type_name


def _value_equal(left: Any, right: Any) -> bool:
    if (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        return isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return len(left) == len(right) and all(
            _value_equal(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            _value_equal(left[key], right[key]) for key in left
        )
    return left == right


@dataclass(frozen=True)
class ReasoningOperator:
    operator_id: str
    input_type: str
    output_type: str
    description: str = ""
    invariants: tuple[str, ...] = ()
    inverse_id: str | None = None
    cost: float = 1.0

    def __post_init__(self) -> None:
        _canonical_identifier(self.operator_id, field_name="operator_id")
        _canonical_identifier(self.input_type, field_name="input_type")
        _canonical_identifier(self.output_type, field_name="output_type")
        if self.inverse_id is not None:
            _canonical_identifier(self.inverse_id, field_name="inverse_id")
        if not isfinite(float(self.cost)) or float(self.cost) < 0.0:
            raise ValueError("operator cost must be finite and non-negative")


@dataclass(frozen=True)
class OperatorStep:
    operator_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _canonical_identifier(self.operator_id, field_name="operator_id")
        object.__setattr__(self, "parameters", dict(self.parameters))


@dataclass(frozen=True)
class ReasoningProgram:
    steps: tuple[OperatorStep, ...]

    def __post_init__(self) -> None:
        if len(self.steps) > 32:
            raise ValueError("reasoning programs are limited to 32 operations")


@dataclass(frozen=True)
class ProgramExecution:
    valid: bool
    final_state: Any
    steps_completed: int
    error: str = ""


class OperatorRegistry:
    """Small fail-closed registry for externally executable reasoning operations."""

    def __init__(self) -> None:
        self._schemas: dict[str, ReasoningOperator] = {}
        self._functions: dict[str, OperatorFn] = {}

    def register(self, schema: ReasoningOperator, function: OperatorFn) -> None:
        if schema.operator_id in self._schemas:
            raise ValueError(f"duplicate reasoning operator: {schema.operator_id}")
        self._schemas[schema.operator_id] = schema
        self._functions[schema.operator_id] = function

    def schema(self, operator_id: str) -> ReasoningOperator:
        try:
            return self._schemas[operator_id]
        except KeyError as exc:
            raise KeyError(f"unknown reasoning operator: {operator_id}") from exc

    def schemas(self) -> tuple[ReasoningOperator, ...]:
        return tuple(self._schemas[key] for key in sorted(self._schemas))

    def execute(self, program: ReasoningProgram, initial_state: Any) -> ProgramExecution:
        state = initial_state
        completed = 0
        for step in program.steps:
            schema = self._schemas.get(step.operator_id)
            function = self._functions.get(step.operator_id)
            if schema is None or function is None:
                return ProgramExecution(
                    False, state, completed, f"unknown operator: {step.operator_id}"
                )
            if not _matches_type(state, schema.input_type):
                return ProgramExecution(
                    False,
                    state,
                    completed,
                    (
                        f"operator {step.operator_id} expected {schema.input_type}, "
                        f"got {_state_type(state)}"
                    ),
                )
            try:
                state = function(state, step.parameters)
            except Exception as exc:
                return ProgramExecution(
                    False,
                    state,
                    completed,
                    f"operator {step.operator_id} failed: {type(exc).__name__}: {exc}",
                )
            completed += 1
            if not _matches_type(state, schema.output_type):
                return ProgramExecution(
                    False,
                    state,
                    completed,
                    (
                        f"operator {step.operator_id} promised {schema.output_type}, "
                        f"produced {_state_type(state)}"
                    ),
                )
        return ProgramExecution(True, state, completed, "")


def _numeric_parameter(parameters: Mapping[str, Any], name: str) -> float:
    value = parameters.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def default_operator_registry() -> OperatorRegistry:
    registry = OperatorRegistry()

    registry.register(
        ReasoningOperator("identity", "any", "any", "Return the state unchanged."),
        lambda state, parameters: state,
    )
    registry.register(
        ReasoningOperator(
            "negate", "number", "number", "Negate a scalar.", inverse_id="negate"
        ),
        lambda state, parameters: -state,
    )
    registry.register(
        ReasoningOperator("add", "number", "number", "Add a finite scalar offset."),
        lambda state, parameters: state + _numeric_parameter(parameters, "value"),
    )
    registry.register(
        ReasoningOperator("scale", "number", "number", "Scale a scalar by a finite factor."),
        lambda state, parameters: state * _numeric_parameter(parameters, "factor"),
    )

    def rotate90(state, parameters):
        x, y = float(state[0]), float(state[1])
        turns = int(parameters.get("turns", 1)) % 4
        for _ in range(turns):
            x, y = -y, x
        return (x, y)

    registry.register(
        ReasoningOperator(
            "rotate90",
            "point2",
            "point2",
            "Rotate a planar point by integer quarter-turns.",
            invariants=("euclidean_norm",),
        ),
        rotate90,
    )
    registry.register(
        ReasoningOperator(
            "reflect_x",
            "point2",
            "point2",
            "Reflect a planar point across the x-axis.",
            invariants=("euclidean_norm",),
            inverse_id="reflect_x",
        ),
        lambda state, parameters: (float(state[0]), -float(state[1])),
    )
    registry.register(
        ReasoningOperator(
            "swap_pair", "pair", "pair", "Swap the two elements of a pair.", inverse_id="swap_pair"
        ),
        lambda state, parameters: (state[1], state[0]),
    )
    registry.register(
        ReasoningOperator("parity", "int", "str", "Classify an integer as even or odd."),
        lambda state, parameters: "even" if state % 2 == 0 else "odd",
    )

    def threshold(state, parameters):
        level = _numeric_parameter(parameters, "threshold")
        value = float(state)
        if isclose(value, level, rel_tol=0.0, abs_tol=1e-12):
            return "equal"
        return "above" if value > level else "below"

    registry.register(
        ReasoningOperator(
            "threshold", "number", "str", "Classify a scalar relative to a threshold."
        ),
        threshold,
    )
    registry.register(
        ReasoningOperator(
            "bool_not", "bool", "bool", "Boolean negation.", inverse_id="bool_not"
        ),
        lambda state, parameters: not state,
    )
    return registry


@dataclass(frozen=True)
class ReasoningCase:
    case_id: str
    structural_family: str
    initial_state: Any
    expected_program: ReasoningProgram
    expected_result: Any
    expected_answer: Any
    surface: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _canonical_identifier(self.case_id, field_name="case_id")
        _canonical_identifier(self.structural_family, field_name="structural_family")
        object.__setattr__(self, "surface", dict(self.surface))


@dataclass(frozen=True)
class ReasoningAttempt:
    case_id: str
    answer: Any
    program: ReasoningProgram

    def __post_init__(self) -> None:
        _canonical_identifier(self.case_id, field_name="case_id")


@dataclass(frozen=True)
class ReasoningContrastSet:
    set_id: str
    canonical: ReasoningCase
    causal_variant: ReasoningCase
    invariant_variant: ReasoningCase

    def __post_init__(self) -> None:
        _canonical_identifier(self.set_id, field_name="set_id")
        if _value_equal(self.canonical.expected_answer, self.causal_variant.expected_answer):
            raise ValueError("causal variant must require an answer change")
        if not _value_equal(
            self.canonical.expected_answer, self.invariant_variant.expected_answer
        ):
            raise ValueError("invariant variant must preserve the expected answer")


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    answer_correct: bool
    program_valid: bool
    program_result_correct: bool
    execution_error: str = ""

    @property
    def fully_correct(self) -> bool:
        return self.answer_correct and self.program_valid and self.program_result_correct


@dataclass(frozen=True)
class ContrastEvaluation:
    set_id: str
    canonical: CaseEvaluation
    causal: CaseEvaluation
    invariant: CaseEvaluation
    pair_correct: bool
    necessary_flip: bool
    invariant_consistency: bool
    all_programs_valid: bool
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "set_id": self.set_id,
            "canonical": self.canonical.__dict__.copy(),
            "causal": self.causal.__dict__.copy(),
            "invariant": self.invariant.__dict__.copy(),
            "pair_correct": self.pair_correct,
            "necessary_flip": self.necessary_flip,
            "invariant_consistency": self.invariant_consistency,
            "all_programs_valid": self.all_programs_valid,
            "score": self.score,
            "interpretation": (
                "behavioral reasoning evaluation only; never proof of consciousness "
                "or mathematical verification"
            ),
        }


def evaluate_case(
    case: ReasoningCase,
    attempt: ReasoningAttempt,
    registry: OperatorRegistry,
) -> CaseEvaluation:
    if attempt.case_id != case.case_id:
        raise ValueError(
            f"attempt case_id {attempt.case_id!r} does not match {case.case_id!r}"
        )
    execution = registry.execute(attempt.program, case.initial_state)
    return CaseEvaluation(
        case_id=case.case_id,
        answer_correct=_value_equal(attempt.answer, case.expected_answer),
        program_valid=execution.valid,
        program_result_correct=(
            execution.valid and _value_equal(execution.final_state, case.expected_result)
        ),
        execution_error=execution.error,
    )


def evaluate_contrast_set(
    task: ReasoningContrastSet,
    attempts: Sequence[ReasoningAttempt],
    registry: OperatorRegistry,
) -> ContrastEvaluation:
    by_id = {attempt.case_id: attempt for attempt in attempts}
    if len(by_id) != len(attempts):
        raise ValueError("duplicate reasoning attempts for one case")
    required = (
        task.canonical.case_id,
        task.causal_variant.case_id,
        task.invariant_variant.case_id,
    )
    missing = [case_id for case_id in required if case_id not in by_id]
    if missing:
        raise ValueError(f"missing reasoning attempts: {missing}")

    canonical = evaluate_case(task.canonical, by_id[task.canonical.case_id], registry)
    causal = evaluate_case(task.causal_variant, by_id[task.causal_variant.case_id], registry)
    invariant = evaluate_case(
        task.invariant_variant, by_id[task.invariant_variant.case_id], registry
    )

    predicted_canonical = by_id[task.canonical.case_id].answer
    predicted_causal = by_id[task.causal_variant.case_id].answer
    predicted_invariant = by_id[task.invariant_variant.case_id].answer

    pair_correct = canonical.answer_correct and causal.answer_correct
    necessary_flip = (
        pair_correct and not _value_equal(predicted_canonical, predicted_causal)
    )
    invariant_consistency = (
        canonical.answer_correct
        and invariant.answer_correct
        and _value_equal(predicted_canonical, predicted_invariant)
    )
    all_programs_valid = all(
        item.program_valid and item.program_result_correct
        for item in (canonical, causal, invariant)
    )
    components = (
        canonical.answer_correct,
        causal.answer_correct,
        invariant.answer_correct,
        necessary_flip,
        invariant_consistency,
        all_programs_valid,
    )
    score = sum(bool(item) for item in components) / len(components)
    return ContrastEvaluation(
        set_id=task.set_id,
        canonical=canonical,
        causal=causal,
        invariant=invariant,
        pair_correct=pair_correct,
        necessary_flip=necessary_flip,
        invariant_consistency=invariant_consistency,
        all_programs_valid=all_programs_valid,
        score=score,
    )


def generate_parity_contrast(seed: int) -> ReasoningContrastSet:
    """Generate a deterministic causal-flip + invariant-control parity task."""
    rng = random.Random(int(seed))
    value = rng.randint(-10_000, 10_000)
    program = ReasoningProgram((OperatorStep("parity"),))
    answer = "even" if value % 2 == 0 else "odd"
    causal_value = value + 1
    causal_answer = "even" if causal_value % 2 == 0 else "odd"
    invariant_value = value + 2
    label = f"x{rng.randrange(1000, 9999)}"
    relabeled = f"q{rng.randrange(1000, 9999)}"
    return ReasoningContrastSet(
        set_id=f"parity-{int(seed)}",
        canonical=ReasoningCase(
            f"parity-{int(seed)}-canonical",
            "parity",
            value,
            program,
            answer,
            answer,
            {"symbol": label, "role": "canonical"},
        ),
        causal_variant=ReasoningCase(
            f"parity-{int(seed)}-causal",
            "parity",
            causal_value,
            program,
            causal_answer,
            causal_answer,
            {"symbol": label, "role": "load-bearing-change"},
        ),
        invariant_variant=ReasoningCase(
            f"parity-{int(seed)}-invariant",
            "parity",
            invariant_value,
            program,
            answer,
            answer,
            {"symbol": relabeled, "role": "structure-preserving-control"},
        ),
    )


@dataclass
class OperatorMastery:
    attempts: int = 0
    pair_correct: int = 0
    necessary_flip: int = 0
    invariant_consistency: int = 0
    program_valid: int = 0

    @property
    def score(self) -> float:
        if self.attempts == 0:
            return 0.0
        denominator = float(self.attempts)
        return (
            self.pair_correct
            + self.necessary_flip
            + self.invariant_consistency
            + self.program_valid
        ) / (4.0 * denominator)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "pair_correct": self.pair_correct,
            "necessary_flip": self.necessary_flip,
            "invariant_consistency": self.invariant_consistency,
            "program_valid": self.program_valid,
            "score": self.score,
        }


class CurriculumMastery:
    """Recency-neutral baseline mastery table for operator-focused curriculum."""

    def __init__(self) -> None:
        self._stats: dict[str, OperatorMastery] = {}

    def record(
        self,
        task: ReasoningContrastSet,
        evaluation: ContrastEvaluation,
    ) -> None:
        operator_ids = {
            step.operator_id
            for case in (task.canonical, task.causal_variant, task.invariant_variant)
            for step in case.expected_program.steps
        }
        for operator_id in operator_ids:
            stats = self._stats.setdefault(operator_id, OperatorMastery())
            stats.attempts += 1
            stats.pair_correct += int(evaluation.pair_correct)
            stats.necessary_flip += int(evaluation.necessary_flip)
            stats.invariant_consistency += int(evaluation.invariant_consistency)
            stats.program_valid += int(evaluation.all_programs_valid)

    def score(self, operator_id: str) -> float:
        return self._stats.get(operator_id, OperatorMastery()).score

    def next_focus(
        self,
        operator_ids: Iterable[str],
        *,
        limit: int = 3,
    ) -> tuple[str, ...]:
        unique = sorted(set(operator_ids))
        unique.sort(
            key=lambda operator_id: (
                self._stats.get(operator_id, OperatorMastery()).score,
                self._stats.get(operator_id, OperatorMastery()).attempts,
                operator_id,
            )
        )
        return tuple(unique[: max(0, int(limit))])

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            operator_id: self._stats[operator_id].to_dict()
            for operator_id in sorted(self._stats)
        }
