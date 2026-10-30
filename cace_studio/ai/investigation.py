"""M.E.R.L.I.N. requirements-first, source-aware, read-only investigation planner.

CACE advisory runtime ONLY: these metadata records neither compute canonical science
nor create proof, verification, approval, network access or human intent findings.

The registry accepts only trusted host-supplied local read-only callables. Plans
have bounded cost, immutable identities, typed stoppages and one-use receipts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Any, Callable, Mapping, Sequence


class ResearchError(ValueError):
    """A local specification or permission-boundary validation failed."""


def _require_text(value: str, label: str, *, limit: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ResearchError(f"{label} must be bounded nonempty text")
    return value.strip()


class ClaimStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED_HYPOTHESIS"
    VERIFIED = "VERIFIED"  # reserved: this module never creates it
    UNKNOWN = "UNKNOWN_ALTERNATIVE"


class PlanState(str, Enum):
    READY = "READY_FOR_LOCAL_READ_ONLY_RUN"
    BLOCKED = "BLOCKED"


class Outcome(str, Enum):
    COMPLETED_ADVISORY = "COMPLETED_ADVISORY_ONLY"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class BlockageKind(str, Enum):
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    TOOL_ERROR = "TOOL_ERROR"
    SOURCE_UNREACHABLE = "SOURCE_UNREACHABLE"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    CONTENT_RESTRICTION = "EXPLICIT_CONTENT_RESTRICTION"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    PLAN_TAMPERED = "PLAN_TAMPERED"
    REPEATED_PLAN = "REPEATED_PLAN"


@dataclass(frozen=True)
class EngineeringSpec:
    goal: str
    domain: str
    acceptance: tuple[str, ...]
    inputs: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    max_steps: int = 12
    max_cost: float = 10.0

    def __post_init__(self) -> None:
        _require_text(self.goal, "goal")
        _require_text(self.domain, "domain", limit=100)
        if not 1 <= len(self.acceptance) <= 32:
            raise ResearchError("at least one and at most 32 acceptance tests required")
        for x in self.acceptance:
            _require_text(x, "acceptance test", limit=1000)
        if len(self.inputs) > 64 or len(self.permissions) > 32:
            raise ResearchError("inputs/permissions exceed bound")
        for x in self.inputs:
            _require_text(x, "input source", limit=1000)
        for x in self.permissions:
            _require_text(x, "permission identifier", limit=100)
        if not isinstance(self.max_steps, int) or not 1 <= self.max_steps <= 64:
            raise ResearchError("max_steps must be between 1 and 64")
        if isinstance(self.max_cost, bool) or not isinstance(self.max_cost, (int, float)) or not math.isfinite(self.max_cost) or self.max_cost < 0:
            raise ResearchError("max_cost must be finite and nonnegative")


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    feature: str
    observed: bool
    source: str
    origin_family: str
    collection_kind: str = "reported"  # observer statement or verified observation are not inferred

    def __post_init__(self) -> None:
        for name in ("evidence_id", "feature", "source", "origin_family"):
            _require_text(getattr(self, name), name)
        if type(self.observed) is not bool:
            raise ResearchError("observed value must be a boolean feature record")
        if self.collection_kind not in {"observed", "reported", "simulated", "archival"}:
            raise ResearchError("unsupported evidence collection kind")


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    description: str
    predictions: Mapping[str, bool]

    def __post_init__(self) -> None:
        _require_text(self.hypothesis_id, "hypothesis id", limit=128)
        _require_text(self.description, "description")
        if self.hypothesis_id == "OTHER_UNMODELED":
            raise ResearchError("OTHER_UNMODELED is automatically reserved")
        if not self.predictions:
            raise ResearchError("hypotheses need testable predictions")
        for key, value in self.predictions.items():
            _require_text(key, "predicted feature", limit=256)
            if type(value) is not bool:
                raise ResearchError("predictions must be boolean feature values")


@dataclass(frozen=True)
class Rating:
    hypothesis_id: str
    support: int
    contradiction: int
    unresolved: int
    ranking_kind: str = "HEURISTIC_NOT_PROBABILITY"
    claim_status: ClaimStatus = ClaimStatus.UNVERIFIED


def evaluate_hypotheses(evidence: Sequence[Evidence], hypotheses: Sequence[Hypothesis]) -> tuple[Rating, ...]:
    """Count provenance-families, not copied reports; never estimate truth likelihood."""
    if not hypotheses or len(hypotheses) > 64:
        raise ResearchError("provide 1 to 64 testable hypotheses")
    ids = [h.hypothesis_id for h in hypotheses]
    if len(ids) != len(set(ids)):
        raise ResearchError("duplicate hypothesis id")
    origin_ids: dict[str, Evidence] = {}
    grouped: dict[tuple[str, str], set[bool]] = {}
    for item in evidence:
        if item.evidence_id in origin_ids and origin_ids[item.evidence_id] != item:
            raise ResearchError("evidence ID reused with conflicting data")
        origin_ids[item.evidence_id] = item
        grouped.setdefault((item.origin_family, item.feature), set()).add(item.observed)
    ratings = []
    for hypothesis in hypotheses:
        support = contradiction = unresolved = 0
        for (_, feature), seen in grouped.items():
            value = hypothesis.predictions.get(feature)
            if value is None or len(seen) != 1:
                unresolved += 1
            elif value in seen:
                support += 1
            else:
                contradiction += 1
        ratings.append(Rating(hypothesis.hypothesis_id, support, contradiction, unresolved))
    ratings.sort(key=lambda v: (v.contradiction, -v.support, v.unresolved, v.hypothesis_id))
    ratings.append(Rating("OTHER_UNMODELED", 0, 0, len(grouped), claim_status=ClaimStatus.UNKNOWN))
    return tuple(ratings)


VALID_LENSES = frozenset({
    "source_audit", "counterexample", "consent_privacy", "inductive", "deductive",
    "abductive", "causal", "bayesian", "fuzzy", "mathematical", "historical",
    "cultural", "geospatial", "ethical", "power", "engineering", "experimental",
    "financial", "security", "metacognition", "communication",
})
PREFERRED_LENSES = {
    "physics": ("mathematical", "causal", "experimental"),
    "signal": ("mathematical", "experimental", "causal"),
    "history": ("historical", "cultural", "abductive"),
    "business": ("financial", "power", "ethical"),
    "security": ("security", "causal", "engineering"),
    "ai": ("engineering", "metacognition", "abductive"),
}


def choose_lenses(domain: str, *, preferred: tuple[str, ...] = ()) -> tuple[str, ...]:
    _require_text(domain, "domain", limit=100)
    if any(x not in VALID_LENSES for x in preferred):
        raise ResearchError("unknown lens")
    ordered = ("source_audit", "counterexample", "consent_privacy", *PREFERRED_LENSES.get(domain, ("inductive", "abductive")), *preferred)
    return tuple(dict.fromkeys(ordered))


@dataclass(frozen=True)
class Blockage:
    kind: BlockageKind
    observed_reason: str
    receipt: str = ""


def audit_blockage(blockage: Blockage, *, trusted_receipts: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Classifies observed blocks without claiming hidden motives or unsupported censorship.

    A receipt string supplied by a caller is evidence of a *report*, not proof
    of its authenticity. Only a separately trusted host-provided receipt list
    can establish that the restriction was explicitly recorded by that source.
    Even then the underlying motive remains unknown.
    """
    _require_text(blockage.observed_reason, "observed reason")
    if not isinstance(blockage.kind, BlockageKind):
        raise ResearchError("unknown blockage type")
    restriction_reported = blockage.kind == BlockageKind.CONTENT_RESTRICTION
    if restriction_reported:
        _require_text(blockage.receipt, "restriction's direct receipt")
    confirmed = restriction_reported and blockage.receipt in trusted_receipts
    interpretation = ("EXPLICIT_RESTRICTION_OBSERVED_SCOPE_LIMITED" if confirmed
                      else "EXPLICIT_RESTRICTION_REPORTED_NOT_AUTHENTICATED" if restriction_reported
                      else "CAUSE_NOT_ESTABLISHED")
    return {
        "kind": blockage.kind.value,
        "observed_reason": blockage.observed_reason,
        "receipt": blockage.receipt or "NOT_AVAILABLE",
        "content_restriction_confirmed": confirmed,
        "interpretation": interpretation,
        "intent_or_motive_established": False,
        "evidence_authority": False,
    }


@dataclass(frozen=True)
class Tool:
    tool_id: str
    capability: str
    effect: str
    cost: float
    handler: Callable[[Mapping[str, Any]], Any]

    def __post_init__(self) -> None:
        _require_text(self.tool_id, "tool id", limit=128)
        _require_text(self.capability, "capability", limit=128)
        if self.effect != "read_only":
            raise ResearchError("only registered read-only local tools are supported")
        if isinstance(self.cost, bool) or not isinstance(self.cost, (float, int)) or not math.isfinite(self.cost) or self.cost < 0:
            raise ResearchError("cost must be finite and nonnegative")
        if not callable(self.handler):
            raise ResearchError("tool handler must be a callable registered by the host")


@dataclass(frozen=True)
class ToolStep:
    tool_id: str
    capability: str
    cost: float


@dataclass(frozen=True)
class ResearchPlan:
    intent: str
    domain: str
    acceptance: tuple[str, ...]
    permissions: tuple[str, ...]
    lenses: tuple[str, ...]
    steps: tuple[ToolStep, ...]
    state: PlanState
    blockages: tuple[Blockage, ...]
    fingerprint: str
    evidence_authority: bool = False
    proof_status: str = "NOT_RUN"
    hardware_status: str = "NOT_MEASURED"


@dataclass(frozen=True)
class Receipt:
    tool_id: str
    capability: str
    status: str
    result_summary: str


@dataclass(frozen=True)
class ResearchResult:
    outcome: Outcome
    receipts: tuple[Receipt, ...] = ()
    blockages: tuple[Blockage, ...] = ()
    evidence_authority: bool = False
    proof_status: str = "NOT_RUN"


def _fingerprint(obj: dict) -> str:
    return sha256(json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


class Investigator:
    """Deterministic advisory local planner; not a credentialed agent executor."""
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._plans: dict[str, ResearchPlan] = {}
        self._used: set[str] = set()

    def register(self, tool: Tool) -> None:
        if tool.tool_id in self._tools:
            raise ResearchError("duplicate tool ID")
        self._tools[tool.tool_id] = tool

    def plan(self, spec: EngineeringSpec, capabilities: Sequence[str]) -> ResearchPlan:
        if not isinstance(spec, EngineeringSpec):
            raise ResearchError("EngineeringSpec must precede tool routing")
        if not capabilities or len(capabilities) > spec.max_steps:
            raise ResearchError("capabilities outside step budget")
        for c in capabilities:
            _require_text(c, "capability", limit=128)
        steps: list[ToolStep] = []
        blockages: list[Blockage] = []
        cost = 0.0
        for capability in capabilities:
            options = sorted((tool for tool in self._tools.values() if tool.capability == capability), key=lambda x: (x.cost, x.tool_id))
            if not options:
                blockages.append(Blockage(BlockageKind.TOOL_UNAVAILABLE, f"no registered tool for {capability}"))
                continue
            tool = options[0]
            cost += tool.cost
            steps.append(ToolStep(tool.tool_id, capability, tool.cost))
        if cost > spec.max_cost:
            blockages.append(Blockage(BlockageKind.RESOURCE_LIMIT, "declared tool cost exceeds engineering budget"))
        state = PlanState.BLOCKED if blockages else PlanState.READY
        if state == PlanState.BLOCKED:
            steps = []  # no partial run when requirements cannot be met
        identity = {
            "intent": spec.goal, "domain": spec.domain,
            "acceptance": spec.acceptance, "permissions": spec.permissions,
            "lenses": choose_lenses(spec.domain), "steps": [asdict(x) for x in steps],
            "state": state.value, "blockages": [asdict(x) for x in blockages],
        }
        key = _fingerprint(identity)
        plan = ResearchPlan(spec.goal, spec.domain, spec.acceptance, spec.permissions,
                            choose_lenses(spec.domain), tuple(steps), state,
                            tuple(blockages), key)
        self._plans[key] = plan
        return plan

    def execute(self, plan: ResearchPlan, context: Mapping[str, Any]) -> ResearchResult:
        if not isinstance(plan, ResearchPlan) or self._plans.get(plan.fingerprint) != plan:
            return ResearchResult(Outcome.BLOCKED, blockages=(Blockage(BlockageKind.PLAN_TAMPERED, "unknown or modified plan"),))
        if plan.fingerprint in self._used:
            return ResearchResult(Outcome.BLOCKED, blockages=(Blockage(BlockageKind.REPEATED_PLAN, "plan already executed; form new approved spec"),))
        self._used.add(plan.fingerprint)  # reserve before running for reentry/loop protection
        if plan.state == PlanState.BLOCKED:
            return ResearchResult(Outcome.BLOCKED, blockages=plan.blockages)
        receipts: list[Receipt] = []
        for step in plan.steps:
            tool = self._tools.get(step.tool_id)
            if tool is None or tool.capability != step.capability or tool.effect != "read_only":
                return ResearchResult(Outcome.BLOCKED, receipts=tuple(receipts), blockages=(Blockage(BlockageKind.TOOL_UNAVAILABLE, "registered tool changed or disappeared"),))
            try:
                result = tool.handler(context)
            except Exception:
                receipts.append(Receipt(step.tool_id, step.capability, "FAILED", "host tool failed; details retained by trusted host"))
                return ResearchResult(Outcome.FAILED, receipts=tuple(receipts), blockages=(Blockage(BlockageKind.TOOL_ERROR, "registered tool raised an exception"),))
            # The value is untrusted metadata, never mathematical verification.
            summary = "result received (not verified)" if result is not None else "empty result (not verified)"
            receipts.append(Receipt(step.tool_id, step.capability, "ADVISORY_RESULT", summary))
        return ResearchResult(Outcome.COMPLETED_ADVISORY, receipts=tuple(receipts))



@dataclass(frozen=True)
class IterationDecision:
    action_id: str
    state_fingerprint: str
    learning_note: str
    status: str
    evidence_authority: bool = False
    proof_status: str = "NOT_RUN"
    hardware_status: str = "NOT_MEASURED"
    authorization_status: str = "NONE_GRANTED"


class IterationLedger:
    """Bounded *proposals* for continuing research after an observed change.

    Fingerprints are caller-supplied identifiers, NOT trusted evidence digests.
    An accepted note marks a new inquiry attempt, NOT learned scientific truth.
    This class cannot run an agent, loop in the background, or approve actions.
    """

    def __init__(self, *, max_attempts: int = 8) -> None:
        if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 32:
            raise ResearchError("max_attempts must be between 1 and 32")
        self.max_attempts = max_attempts
        self._records: list[IterationDecision] = []
        self._seen: set[tuple[str, str]] = set()

    @property
    def records(self) -> tuple[IterationDecision, ...]:
        return tuple(self._records)

    def propose(self, action_id: str, state_fingerprint: str, learning_note: str) -> IterationDecision:
        _require_text(action_id, "action id", limit=128)
        _require_text(learning_note, "learning note", limit=2048)
        if not isinstance(state_fingerprint, str) or len(state_fingerprint) != 64 or any(c not in "0123456789abcdef" for c in state_fingerprint):
            raise ResearchError("state fingerprint must have lowercase SHA-256 format")
        base = dict(action_id=action_id, state_fingerprint=state_fingerprint, learning_note=learning_note)
        if len(self._records) >= self.max_attempts:
            return IterationDecision(**base, status="STOP_BUDGET")
        key = (action_id, state_fingerprint)
        if key in self._seen:
            return IterationDecision(**base, status="HOLD_NO_NEW_OBSERVATION")
        self._seen.add(key)
        record = IterationDecision(**base, status="CONTINUE_WITH_REVIEW")
        self._records.append(record)
        return record
