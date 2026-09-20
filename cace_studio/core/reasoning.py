from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Callable, Iterable, Mapping, Sequence


class ReasoningError(RuntimeError):
    """Base error for advisory reasoning/operator execution."""


class UnknownReasoningOperator(ReasoningError):
    pass


class DuplicateReasoningOperator(ReasoningError):
    pass


class NativeReasoningBackendUnavailable(ReasoningError):
    pass


@dataclass(frozen=True)
class ReasoningOperator:
    operator_id: str
    version: str
    title: str
    input_types: tuple[str, ...]
    output_type: str
    preconditions: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    inverse_operator_id: str | None = None
    commutes_with: tuple[str, ...] = ()
    implementation_ref: str = ""
    checker_refs: tuple[str, ...] = ()
    cost_class: str = "backend-dependent"
    evidence_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self.operator_id or self.operator_id != self.operator_id.strip():
            raise ValueError("operator_id must be a non-empty canonical string")
        if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_.-" for ch in self.operator_id):
            raise ValueError("operator_id contains unsupported characters")
        if not self.version:
            raise ValueError("version must be non-empty")
        if not self.title:
            raise ValueError("title must be non-empty")
        if not self.input_types or any(not x for x in self.input_types):
            raise ValueError("input_types must contain at least one non-empty type")
        if not self.output_type:
            raise ValueError("output_type must be non-empty")
        if not self.implementation_ref:
            raise ValueError("implementation_ref must be non-empty")
        if self.cost_class not in {
            "constant",
            "linear",
            "quadratic",
            "cubic",
            "bounded-enumeration",
            "backend-dependent",
        }:
            raise ValueError("unsupported cost_class")
        if len(set(self.preconditions)) != len(self.preconditions):
            raise ValueError("preconditions must be unique")
        if len(set(self.invariants)) != len(self.invariants):
            raise ValueError("invariants must be unique")
        if len(set(self.commutes_with)) != len(self.commutes_with):
            raise ValueError("commutes_with must be unique")
        if len(set(self.checker_refs)) != len(self.checker_refs):
            raise ValueError("checker_refs must be unique")

    def descriptor(self) -> dict[str, Any]:
        return {
            "schema_version": "cace-reasoning-operator-v1",
            "operator_id": self.operator_id,
            "version": self.version,
            "title": self.title,
            "input_types": list(self.input_types),
            "output_type": self.output_type,
            "preconditions": list(self.preconditions),
            "invariants": list(self.invariants),
            "inverse_operator_id": self.inverse_operator_id,
            "commutes_with": list(self.commutes_with),
            "implementation_ref": self.implementation_ref,
            "checker_refs": list(self.checker_refs),
            "cost_class": self.cost_class,
            "evidence_authority": False,
        }

    def semantic_sha256(self) -> str:
        raw = json.dumps(
            self.descriptor(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return sha256(raw).hexdigest()


@dataclass(frozen=True)
class ReasoningStep:
    operator_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReasoningPlanResult:
    initial_state: Any
    final_state: Any
    steps_executed: tuple[str, ...]
    evidence_authority: bool = field(default=False, init=False)


@dataclass(frozen=True)
class PairedInterventionResult:
    baseline_correct: bool
    intervention_correct: bool
    expected_flip: bool
    observed_flip: bool
    load_bearing: bool
    pair_correct: bool
    flip_consistent: bool
    evidence_authority: bool = field(default=False, init=False)


@dataclass(frozen=True)
class SymmetryReductionResult:
    raw_states: int
    canonical_states: int
    eliminated_states: int
    reduction_fraction: float
    idempotent: bool
    evidence_authority: bool = field(default=False, init=False)


Executor = Callable[[Any, Mapping[str, Any]], Any]


class ReasoningOperatorRegistry:
    """Typed advisory operator registry with no evidence authority."""

    def __init__(self) -> None:
        self._operators: dict[str, ReasoningOperator] = {}
        self._executors: dict[str, Executor] = {}

    def register(self, operator: ReasoningOperator, executor: Executor) -> None:
        if operator.operator_id in self._operators:
            raise DuplicateReasoningOperator(operator.operator_id)
        if not callable(executor):
            raise TypeError("reasoning operator executor must be callable")
        self._operators[operator.operator_id] = operator
        self._executors[operator.operator_id] = executor

    def contains(self, operator_id: str) -> bool:
        return operator_id in self._operators

    def get(self, operator_id: str) -> ReasoningOperator:
        try:
            return self._operators[operator_id]
        except KeyError as exc:
            raise UnknownReasoningOperator(operator_id) from exc

    def descriptors(self) -> list[dict[str, Any]]:
        return [
            self._operators[key].descriptor()
            for key in sorted(self._operators)
        ]

    def execute(
        self,
        operator_id: str,
        state: Any,
        parameters: Mapping[str, Any] | None = None,
    ) -> Any:
        self.get(operator_id)
        return self._executors[operator_id](state, parameters or {})

    def execute_plan(
        self,
        initial_state: Any,
        steps: Iterable[ReasoningStep],
    ) -> ReasoningPlanResult:
        state = initial_state
        executed: list[str] = []
        for step in steps:
            state = self.execute(step.operator_id, state, step.parameters)
            executed.append(step.operator_id)
        return ReasoningPlanResult(
            initial_state=initial_state,
            final_state=state,
            steps_executed=tuple(executed),
        )


def evaluate_paired_intervention(
    *,
    baseline_expected: Any,
    baseline_actual: Any,
    intervention_expected: Any,
    intervention_actual: Any,
    load_bearing: bool,
) -> PairedInterventionResult:
    baseline_correct = baseline_actual == baseline_expected
    intervention_correct = intervention_actual == intervention_expected
    expected_flip = baseline_expected != intervention_expected
    observed_flip = baseline_actual != intervention_actual
    return PairedInterventionResult(
        baseline_correct=baseline_correct,
        intervention_correct=intervention_correct,
        expected_flip=expected_flip,
        observed_flip=observed_flip,
        load_bearing=load_bearing,
        pair_correct=baseline_correct and intervention_correct,
        flip_consistent=(observed_flip == expected_flip)
        and (expected_flip == load_bearing),
    )


def evaluate_symmetry_reduction(
    states: Sequence[Any],
    canonicalize: Callable[[Any], Any],
    *,
    key: Callable[[Any], str] = repr,
) -> SymmetryReductionResult:
    if not states:
        return SymmetryReductionResult(
            raw_states=0,
            canonical_states=0,
            eliminated_states=0,
            reduction_fraction=0.0,
            idempotent=True,
        )

    canonical = [canonicalize(state) for state in states]
    canonical_keys = {key(value) for value in canonical}
    idempotent = all(
        key(canonicalize(value)) == key(value)
        for value in canonical
    )
    raw_count = len(states)
    canonical_count = len(canonical_keys)
    eliminated = raw_count - canonical_count
    return SymmetryReductionResult(
        raw_states=raw_count,
        canonical_states=canonical_count,
        eliminated_states=eliminated,
        reduction_fraction=eliminated / raw_count,
        idempotent=idempotent,
    )


def _require_no_parameters(parameters: Mapping[str, Any]) -> None:
    if parameters:
        raise ReasoningError(
            f"operator does not accept parameters: {sorted(parameters)}"
        )


def _require_parameter(parameters: Mapping[str, Any], name: str) -> Any:
    if name not in parameters:
        raise ReasoningError(f"missing reasoning operator parameter: {name}")
    return parameters[name]


def build_exact_geometric_registry(native_module: Any) -> ReasoningOperatorRegistry:
    """Register exact C++/pybind-backed geometric reasoning primitives.

    The native module is normally _cace_runtime. Dependency injection keeps
    regression tests independent from whether pybind11 is installed locally.
    Mathematical algorithms are not reimplemented here.
    """

    required_symbols = (
        "ExactPermutation",
        "FinitePermutationGroup",
        "ExactExterior",
        "ExactAffineMap",
        "ExactSimplex",
    )
    missing = [name for name in required_symbols if not hasattr(native_module, name)]
    if missing:
        raise NativeReasoningBackendUnavailable(
            "exact reasoning backend is missing: " + ", ".join(missing)
        )

    registry = ReasoningOperatorRegistry()

    def add(
        operator_id: str,
        title: str,
        input_types: tuple[str, ...],
        output_type: str,
        executor: Executor,
        *,
        preconditions: tuple[str, ...] = (),
        invariants: tuple[str, ...] = (),
        inverse_operator_id: str | None = None,
        cost_class: str = "backend-dependent",
        checker_refs: tuple[str, ...] = (),
    ) -> None:
        registry.register(
            ReasoningOperator(
                operator_id=operator_id,
                version="1",
                title=title,
                input_types=input_types,
                output_type=output_type,
                preconditions=preconditions,
                invariants=invariants,
                inverse_operator_id=inverse_operator_id,
                implementation_ref="cpp/_cace_runtime",
                checker_refs=checker_refs,
                cost_class=cost_class,
            ),
            executor,
        )

    add(
        "math.combinatorics.permutation.inverse",
        "Invert exact permutation",
        ("ExactPermutation",),
        "ExactPermutation",
        lambda state, params: (
            _require_no_parameters(params),
            state.inverse(),
        )[1],
        invariants=("degree preserved", "p.compose(p.inverse()) = identity"),
        inverse_operator_id="math.combinatorics.permutation.inverse",
        cost_class="linear",
    )

    add(
        "math.combinatorics.permutation.compose",
        "Compose exact permutations",
        ("ExactPermutation", "ExactPermutation"),
        "ExactPermutation",
        lambda state, params: state.compose(
            _require_parameter(params, "inner")
        ),
        preconditions=("same permutation degree",),
        invariants=("bijection preserved",),
        cost_class="linear",
    )

    add(
        "math.combinatorics.permutation.act_coordinates",
        "Apply permutation to exact coordinates",
        ("ExactVector", "ExactPermutation"),
        "ExactVector",
        lambda state, params: _require_parameter(
            params, "permutation"
        ).act_coordinates(state),
        preconditions=("vector dimension equals permutation degree",),
        invariants=("coordinate multiset preserved",),
        cost_class="linear",
    )

    add(
        "math.combinatorics.permutation.act_exterior",
        "Apply permutation to exact exterior element",
        ("ExactExterior", "ExactPermutation"),
        "ExactExterior",
        lambda state, params: _require_parameter(
            params, "permutation"
        ).act_exterior(state),
        preconditions=("exterior dimension equals permutation degree",),
        invariants=("grade preserved", "orientation sign tracked exactly"),
        cost_class="linear",
    )

    add(
        "math.combinatorics.group.canonical_coordinate_representative",
        "Canonicalize exact coordinates under finite group",
        ("ExactVector", "FinitePermutationGroup"),
        "ExactVector",
        lambda state, params: _require_parameter(
            params, "group"
        ).canonical_coordinate_representative(state),
        preconditions=("vector dimension equals group degree",),
        invariants=("canonicalization constant across group orbit",),
        cost_class="bounded-enumeration",
    )

    add(
        "math.combinatorics.group.canonical_exterior_representative",
        "Canonicalize exact exterior element under finite group",
        ("ExactExterior", "FinitePermutationGroup"),
        "ExactExterior",
        lambda state, params: _require_parameter(
            params, "group"
        ).canonical_exterior_representative(state),
        preconditions=("exterior dimension equals group degree",),
        invariants=("canonicalization constant across group orbit",),
        cost_class="bounded-enumeration",
    )

    add(
        "math.exterior.wedge",
        "Exact wedge product",
        ("ExactExterior", "ExactExterior"),
        "ExactExterior",
        lambda state, params: state.wedge(
            _require_parameter(params, "rhs")
        ),
        preconditions=("same exterior dimension",),
        invariants=("grade additive on homogeneous nonzero terms",),
        cost_class="quadratic",
    )

    add(
        "math.exterior.hodge_dual",
        "Exact Euclidean Hodge dual",
        ("ExactExterior",),
        "ExactExterior",
        lambda state, params: (
            _require_no_parameters(params),
            state.hodge_dual(),
        )[1],
        preconditions=("ordered orthonormal Euclidean basis convention",),
        invariants=("complementary grade",),
        cost_class="linear",
    )

    add(
        "math.exterior.pushforward",
        "Exact exterior pushforward",
        ("ExactExterior", "ExactMatrix"),
        "ExactExterior",
        lambda state, params: state.pushforward(
            _require_parameter(params, "linear")
        ),
        preconditions=("linear input dimension equals exterior dimension",),
        invariants=("wedge transport respects linear action",),
        cost_class="backend-dependent",
    )

    add(
        "math.geometry.affine.apply",
        "Apply exact affine map",
        ("ExactVector", "ExactAffineMap"),
        "ExactVector",
        lambda state, params: _require_parameter(
            params, "affine"
        ).apply(state),
        preconditions=("point dimension equals affine input dimension",),
        invariants=("exact Ax+b semantics",),
        cost_class="quadratic",
    )

    add(
        "math.geometry.simplex.barycentric",
        "Exact simplex barycentric coordinates",
        ("ExactVector", "ExactSimplex"),
        "ExactVector",
        lambda state, params: _require_parameter(
            params, "simplex"
        ).barycentric_coordinates(state),
        preconditions=(
            "simplex nondegenerate",
            "point dimension equals simplex dimension",
        ),
        invariants=("coordinates sum exactly to one",),
        cost_class="cubic",
    )

    return registry


def load_exact_geometric_registry() -> ReasoningOperatorRegistry:
    try:
        import _cace_runtime as native_module
    except Exception as exc:  # pragma: no cover - environment dependent
        raise NativeReasoningBackendUnavailable(
            "optional _cace_runtime pybind module is unavailable"
        ) from exc
    return build_exact_geometric_registry(native_module)
