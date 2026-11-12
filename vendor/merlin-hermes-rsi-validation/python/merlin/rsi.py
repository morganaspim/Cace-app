"""Small, dependency-free RSI kernel for evidence-gated skill improvement.

Inspired by failure-driven skill induction (EvoSkill) and reproducible agent
evaluation (Inspect AI). This module stores declarative procedures, compares
identical baseline/candidate suites, and emits a review packet. It never
executes candidate code, edits Merlin, changes evaluators, or auto-promotes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Iterable


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _is_sha(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class SkillProcedure:
    skill_id: str
    version: int
    purpose: str
    trigger_conditions: tuple[str, ...]
    steps: tuple[str, ...]
    guardrails: tuple[str, ...]
    source_failure_ids: tuple[str, ...]

    def validate(self) -> None:
        if not isinstance(self.skill_id, str) or not self.skill_id.strip() or len(self.skill_id) > 100 or type(self.version) is not int or self.version < 1:
            raise ValueError("skill identity or version is invalid")
        if not isinstance(self.purpose, str) or not self.purpose.strip() or len(self.purpose) > 500:
            raise ValueError("skill purpose is required and bounded")
        for name, values in (
            ("trigger_conditions", self.trigger_conditions),
            ("steps", self.steps),
            ("guardrails", self.guardrails),
            ("source_failure_ids", self.source_failure_ids),
        ):
            if not isinstance(values, tuple) or not values or any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in values):
                raise ValueError(f"{name} must contain non-empty bounded strings")
        if len(self.steps) > 20 or len(self.guardrails) > 20 or len(self.source_failure_ids) > 100:
            raise ValueError("skill procedure exceeds bounded collection size")

    @property
    def sha256(self) -> str:
        self.validate()
        return _digest(asdict(self))


@dataclass(frozen=True)
class FailureTrajectory:
    """Redacted, content-addressed summary of one failed task and its repair."""
    failure_id: str
    failure_signature: str
    trigger_condition: str
    corrective_steps: tuple[str, ...]
    source_commit_sha: str
    source_artifact_sha256: str

    def validate(self) -> None:
        if (not isinstance(self.failure_id, str) or not self.failure_id.strip()
                or not isinstance(self.failure_signature, str) or not self.failure_signature.strip()
                or not isinstance(self.trigger_condition, str) or not self.trigger_condition.strip()):
            raise ValueError("failure trajectory requires identity, signature, and trigger")
        if len(self.failure_signature) > 160 or len(self.trigger_condition) > 300:
            raise ValueError("failure signature or trigger exceeds bounds")
        if not isinstance(self.corrective_steps, tuple) or not self.corrective_steps or len(self.corrective_steps) > 10:
            raise ValueError("failure trajectory requires 1 to 10 corrective steps")
        if any(not isinstance(step, str) or not step.strip() or len(step) > 300 for step in self.corrective_steps):
            raise ValueError("corrective steps must be non-empty and bounded")
        if not isinstance(self.source_commit_sha, str) or len(self.source_commit_sha) != 40 or any(c not in "0123456789abcdef" for c in self.source_commit_sha):
            raise ValueError("source commit must be a lowercase 40-character Git SHA")
        if not _is_sha(self.source_artifact_sha256):
            raise ValueError("source artifact must have a SHA-256 digest")


def induce_skill_candidate(
    *,
    skill_id: str,
    version: int,
    purpose: str,
    trajectories: Iterable[FailureTrajectory],
    guardrails: tuple[str, ...],
) -> SkillProcedure:
    """Induce a declarative candidate only from repeated, convergent failures.

    It keeps the ordered intersection of corrective steps across all supplied
    trajectories. It does not invent missing steps or execute generated text.
    """
    rows = tuple(trajectories)
    if len(rows) < 2:
        raise ValueError("at least two independent failure trajectories are required")
    for row in rows:
        row.validate()
    ids = [row.failure_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("failure trajectory IDs must be unique")
    signatures = {row.failure_signature for row in rows}
    if len(signatures) != 1:
        raise ValueError("failure trajectories must share one normalized signature")
    common = set(rows[0].corrective_steps)
    for row in rows[1:]:
        common.intersection_update(row.corrective_steps)
    ordered_steps = tuple(step for step in rows[0].corrective_steps if step in common)
    if not ordered_steps:
        raise ValueError("failure trajectories have no convergent corrective steps")
    candidate = SkillProcedure(
        skill_id=skill_id, version=version, purpose=purpose,
        trigger_conditions=tuple(sorted({row.trigger_condition for row in rows})),
        steps=ordered_steps, guardrails=guardrails,
        source_failure_ids=tuple(sorted(ids)),
    )
    candidate.validate()
    return candidate


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    split: str
    input_sha256: str

    def validate(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip() or len(self.case_id) > 128 or self.split not in {"train", "heldout"} or not _is_sha(self.input_sha256):
            raise ValueError("invalid evaluation case identity, split, or input digest")


@dataclass(frozen=True)
class CaseOutcome:
    case_id: str
    passed: bool
    resource_units: int = 0

    def validate(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip() or type(self.passed) is not bool or type(self.resource_units) is not int or self.resource_units < 0:
            raise ValueError("invalid case outcome")


@dataclass(frozen=True)
class EvaluationEvidence:
    skill_sha256: str
    suite_sha256: str
    evaluator_sha256: str
    runner_id: str
    runner_revision: str
    outcomes: tuple[CaseOutcome, ...]

    def validate(self, cases: Iterable[EvalCase]) -> None:
        for digest in (self.skill_sha256, self.suite_sha256, self.evaluator_sha256):
            if not _is_sha(digest):
                raise ValueError("evaluation evidence requires SHA-256 digests")
        if not isinstance(self.runner_id, str) or not self.runner_id.strip() or not isinstance(self.runner_revision, str) or not self.runner_revision.strip():
            raise ValueError("runner identity and revision are required")
        case_list = tuple(cases)
        for case in case_list:
            case.validate()
        expected = {case.case_id for case in case_list}
        actual = [outcome.case_id for outcome in self.outcomes]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("evaluation outcomes must cover every suite case exactly once")
        for outcome in self.outcomes:
            outcome.validate()
        if len([c for c in case_list if c.split == "heldout"]) < 2:
            raise ValueError("at least two held-out cases are required")


def suite_digest(cases: Iterable[EvalCase]) -> str:
    normalized = sorted((asdict(case) for case in cases), key=lambda row: row["case_id"])
    return _digest(normalized)


def outcome_digest(evidence: EvaluationEvidence) -> str:
    normalized = {
        "skill_sha256": evidence.skill_sha256,
        "suite_sha256": evidence.suite_sha256,
        "evaluator_sha256": evidence.evaluator_sha256,
        "runner_id": evidence.runner_id,
        "runner_revision": evidence.runner_revision,
        "outcomes": sorted((asdict(item) for item in evidence.outcomes), key=lambda row: row["case_id"]),
    }
    return _digest(normalized)


@dataclass(frozen=True)
class EvolutionDecision:
    schema: str
    status: str
    baseline_heldout_accuracy: float
    candidate_heldout_accuracy: float
    heldout_delta: float
    heldout_regressions: tuple[str, ...]
    resource_units: int
    within_resource_budget: bool
    baseline_result_sha256: str
    candidate_result_sha256: str
    candidate_skill_sha256: str
    reason: str
    automatic_promotion: bool = False
    human_review_required: bool = True


def compare_skill_evaluations(
    *,
    baseline_skill: SkillProcedure,
    candidate_skill: SkillProcedure,
    cases: Iterable[EvalCase],
    baseline: EvaluationEvidence,
    candidate: EvaluationEvidence,
    max_resource_units: int,
) -> EvolutionDecision:
    """Compare same cases/evaluator/runner; only qualify strict held-out gains."""
    baseline_skill.validate()
    candidate_skill.validate()
    if baseline_skill.skill_id != candidate_skill.skill_id or candidate_skill.version <= baseline_skill.version:
        raise ValueError("candidate must be a newer version of the same skill")
    case_list = tuple(cases)
    if len(case_list) < 3 or len({c.case_id for c in case_list}) != len(case_list):
        raise ValueError("evaluation suite requires unique cases and at least three cases")
    if not any(c.split == "train" for c in case_list) or sum(c.split == "heldout" for c in case_list) < 2:
        raise ValueError("evaluation suite requires training cases and at least two held-out cases")
    expected_suite = suite_digest(case_list)
    baseline.validate(case_list)
    candidate.validate(case_list)
    if baseline.suite_sha256 != expected_suite or candidate.suite_sha256 != expected_suite:
        raise ValueError("baseline and candidate must use the exact declared evaluation suite")
    if baseline.skill_sha256 != baseline_skill.sha256 or candidate.skill_sha256 != candidate_skill.sha256:
        raise ValueError("evaluation evidence does not match the exact skill versions")
    if (baseline.evaluator_sha256, baseline.runner_id, baseline.runner_revision) != (
        candidate.evaluator_sha256, candidate.runner_id, candidate.runner_revision
    ):
        raise ValueError("evaluator and runner identity must remain fixed during comparison")
    if type(max_resource_units) is not int or max_resource_units < 0:
        raise ValueError("max_resource_units must be a nonnegative integer")

    base = {item.case_id: item for item in baseline.outcomes}
    cand = {item.case_id: item for item in candidate.outcomes}
    heldout_ids = sorted(c.case_id for c in case_list if c.split == "heldout")
    base_accuracy = sum(base[key].passed for key in heldout_ids) / len(heldout_ids)
    candidate_accuracy = sum(cand[key].passed for key in heldout_ids) / len(heldout_ids)
    regressions = tuple(key for key in heldout_ids if base[key].passed and not cand[key].passed)
    resources = sum(item.resource_units for item in candidate.outcomes)
    within_budget = resources <= max_resource_units
    delta = candidate_accuracy - base_accuracy
    if regressions:
        status, reason = "BLOCKED", "heldout_regression"
    elif not within_budget:
        status, reason = "BLOCKED", "resource_budget_exceeded"
    elif delta <= 0:
        status, reason = "NO_IMPROVEMENT", "candidate_did_not_improve_heldout_accuracy"
    else:
        status, reason = "ELIGIBLE_FOR_REVIEW", "heldout_gain_without_regression"
    return EvolutionDecision(
        schema="merlin-rsi-evaluation/1", status=status,
        baseline_heldout_accuracy=base_accuracy,
        candidate_heldout_accuracy=candidate_accuracy,
        heldout_delta=delta, heldout_regressions=regressions,
        resource_units=resources, within_resource_budget=within_budget,
        baseline_result_sha256=outcome_digest(baseline),
        candidate_result_sha256=outcome_digest(candidate),
        candidate_skill_sha256=candidate_skill.sha256, reason=reason,
    )
