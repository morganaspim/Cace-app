from __future__ import annotations

"""Repository-wide evidence and claim-promotion policy.

The purpose of this module is deliberately conservative: computational evidence may suggest a
conjecture, and Lean may certify a formal statement, but CACE must not silently collapse those
very different states into the word "solved".

In particular, an open-problem-resolution claim is never public-claim eligible from CACE's own
numerical, symbolic, interval, or formal output alone. It additionally needs an independently
reproduced *same artifact* and an external review bound to that same artifact digest.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable


class ClaimScope(str, Enum):
    ORDINARY = "ordinary"
    OPEN_PROBLEM_RESOLUTION = "open-problem-resolution"


class ClaimStage(str, Enum):
    RESEARCH_CANDIDATE = "research-candidate"
    FORMAL_CANDIDATE = "formal-candidate"
    REPRODUCED_FORMAL_CANDIDATE = "reproduced-formal-candidate"
    EXTERNALLY_REVIEWED_RESOLUTION = "externally-reviewed-resolution"


def _is_sha256_digest(value: str | None) -> bool:
    if value is None:
        return False
    digest = value.strip().lower()
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


@dataclass(frozen=True)
class IndependentReproductionAttestation:
    """Externally supplied record that a concrete claim artifact was independently reproduced."""

    reproducer_identity: str
    artifact_sha256: str
    decision: str = "reproduced"
    independent: bool = True
    source: str = "external"

    def valid_for_promotion(self, expected_artifact_sha256: str | None = None) -> bool:
        digest = self.artifact_sha256.strip().lower()
        expected = expected_artifact_sha256.strip().lower() if expected_artifact_sha256 else None
        return (
            self.source == "external"
            and self.independent
            and bool(self.reproducer_identity.strip())
            and self.decision.lower() in {"reproduced", "verified", "pass", "passed"}
            and _is_sha256_digest(digest)
            and (expected is None or digest == expected)
        )


@dataclass(frozen=True)
class ExternalReviewAttestation:
    """A record supplied from outside the theorem-producing CACE run.

    `artifact_sha256` binds the review to a concrete manuscript/proof artifact. This dataclass does
    not pretend to establish the human reviewer's identity cryptographically; that remains an
    external trust boundary and is reported as such.
    """

    reviewer_identity: str
    artifact_sha256: str
    decision: str
    independent: bool = True
    source: str = "external"

    def valid_for_promotion(self, expected_artifact_sha256: str | None = None) -> bool:
        digest = self.artifact_sha256.strip().lower()
        expected = expected_artifact_sha256.strip().lower() if expected_artifact_sha256 else None
        return (
            self.source == "external"
            and self.independent
            and bool(self.reviewer_identity.strip())
            and self.decision.lower() in {"approve", "accepted", "verified"}
            and _is_sha256_digest(digest)
            and (expected is None or digest == expected)
        )


@dataclass(frozen=True)
class ClaimEvidence:
    unresolved_obligations: tuple[str, ...] = ()
    formal_kernel_verified: bool = False
    axiom_audit_passed: bool = False
    pinned_ci_passed: bool = False
    exact_statement_digest: str | None = None
    # Legacy informational count retained for compatibility. It is never sufficient for promotion.
    independent_reproductions: int = 0
    reproduction_attestations: tuple[IndependentReproductionAttestation, ...] = ()
    external_reviews: tuple[ExternalReviewAttestation, ...] = ()
    numerical_evidence: bool = False
    symbolic_evidence: bool = False
    interval_evidence: bool = False


@dataclass(frozen=True)
class ClaimDecision:
    scope: ClaimScope
    stage: ClaimStage
    public_resolution_claim_allowed: bool
    blockers: tuple[str, ...] = field(default_factory=tuple)
    trust_boundary: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scope"] = self.scope.value
        d["stage"] = self.stage.value
        return d


def _formal_gate(evidence: ClaimEvidence) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if evidence.unresolved_obligations:
        blockers.append("unresolved-proof-obligations")
    if not evidence.formal_kernel_verified:
        blockers.append("formal-kernel-verification-missing")
    if not evidence.axiom_audit_passed:
        blockers.append("axiom-audit-missing")
    if not evidence.pinned_ci_passed:
        blockers.append("pinned-ci-missing")
    if evidence.exact_statement_digest is None:
        blockers.append("exact-statement-digest-missing")
    elif not _is_sha256_digest(evidence.exact_statement_digest):
        blockers.append("exact-statement-digest-invalid")
    return not blockers, blockers


def evaluate_claim(scope: ClaimScope, evidence: ClaimEvidence) -> ClaimDecision:
    """Evaluate the strongest wording CACE is permitted to use for a claim.

    This is fail-closed. Numerical/symbolic/interval evidence cannot substitute for the formal
    gate. For an open-problem resolution, even a fully kernel-checked theorem remains only a formal
    candidate until the *same exact artifact* has an independent reproduction and external review.
    """

    formal_ok, blockers = _formal_gate(evidence)
    trust_boundary = [
        "Lean kernel and pinned dependency toolchain",
        "CI runner/execution environment",
    ]

    if not formal_ok:
        return ClaimDecision(
            scope=scope,
            stage=ClaimStage.RESEARCH_CANDIDATE,
            public_resolution_claim_allowed=False,
            blockers=tuple(blockers),
            trust_boundary=tuple(trust_boundary),
        )

    if scope is ClaimScope.ORDINARY:
        return ClaimDecision(
            scope=scope,
            stage=ClaimStage.FORMAL_CANDIDATE,
            public_resolution_claim_allowed=False,
            blockers=("external-publication-or-review-status-not-assessed",),
            trust_boundary=tuple(trust_boundary),
        )

    digest = evidence.exact_statement_digest
    valid_reproductions = tuple(
        r for r in evidence.reproduction_attestations if r.valid_for_promotion(digest)
    )
    if not valid_reproductions:
        blocker = (
            "artifact-bound-independent-reproduction-missing"
            if evidence.independent_reproductions <= 0
            else "legacy-reproduction-count-not-artifact-bound"
        )
        return ClaimDecision(
            scope=scope,
            stage=ClaimStage.FORMAL_CANDIDATE,
            public_resolution_claim_allowed=False,
            blockers=(blocker, "external-review-missing"),
            trust_boundary=tuple(trust_boundary),
        )

    trust_boundary.append("independent reproduction identity/independence provenance")
    valid_reviews = tuple(r for r in evidence.external_reviews if r.valid_for_promotion(digest))
    if not valid_reviews:
        return ClaimDecision(
            scope=scope,
            stage=ClaimStage.REPRODUCED_FORMAL_CANDIDATE,
            public_resolution_claim_allowed=False,
            blockers=("artifact-bound-external-review-missing-or-invalid",),
            trust_boundary=tuple(trust_boundary),
        )

    trust_boundary.append(
        "external reviewer identity/independence is an external trust boundary, not established by CACE"
    )
    return ClaimDecision(
        scope=scope,
        stage=ClaimStage.EXTERNALLY_REVIEWED_RESOLUTION,
        public_resolution_claim_allowed=True,
        blockers=(),
        trust_boundary=tuple(trust_boundary),
    )


def research_candidate_decision(
    *,
    unresolved_obligations: Iterable[str] = (),
    numerical_evidence: bool = False,
    symbolic_evidence: bool = False,
    interval_evidence: bool = False,
) -> ClaimDecision:
    """Convenience entry point for discovery engines that are intentionally pre-proof."""

    return evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        ClaimEvidence(
            unresolved_obligations=tuple(sorted(set(unresolved_obligations))),
            numerical_evidence=numerical_evidence,
            symbolic_evidence=symbolic_evidence,
            interval_evidence=interval_evidence,
        ),
    )


OPEN_PROBLEM_MODULE_CATEGORIES = frozenset({"Theorem Discovery", "Reliability Theorem"})
RESERVED_PUBLIC_PROMOTION_KEYS = frozenset({
    "public_resolution_claim_allowed",
    "resolution_claim_allowed",
    "open_problem_resolved",
    "famous_open_problem_resolved",
    "reliability_promotable",
})


def _collect_open_obligations(value: Any) -> set[str]:
    """Conservatively recover named open obligations from nested discovery-module outputs."""

    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"unresolved", "open", "blocking_nodes", "unresolved_obligations"}:
                if isinstance(child, (list, tuple, set)):
                    found.update(str(x) for x in child)
            found.update(_collect_open_obligations(child))
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            found.update(_collect_open_obligations(child))
    return found


def unsafe_self_promotion_paths(value: Any, prefix: str = "") -> tuple[str, ...]:
    """Find reserved public-promotion flags that a module attempted to set truthy itself."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in RESERVED_PUBLIC_PROMOTION_KEYS and bool(child):
                found.append(path)
            found.extend(unsafe_self_promotion_paths(child, path))
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            path = f"{prefix}[{i}]" if prefix else f"[{i}]"
            found.extend(unsafe_self_promotion_paths(child, path))
    return tuple(found)


def fail_closed_module_decision(category: str, proof_status: Any, outputs: Any) -> ClaimDecision | None:
    """Framework-level guard for theorem-discovery/reliability modules.

    Module outputs are deliberately *not* trusted to self-assert formal verification, reproduction,
    review, or public resolution status. For open-problem research categories, the executor records
    a research-candidate sidecar decision using only conservative evidence classification and any
    named open obligations discoverable in the output. Formal promotion must go through
    `evaluate_claim` with externally supplied, artifact-bound evidence.
    """

    if category not in OPEN_PROBLEM_MODULE_CATEGORIES:
        return None

    evidence_values = {
        getattr(item, "value", str(item)) for item in getattr(proof_status, "evidence", set())
    }
    unresolved = _collect_open_obligations(outputs)
    return research_candidate_decision(
        unresolved_obligations=unresolved,
        numerical_evidence="numerical" in evidence_values,
        symbolic_evidence="symbolic" in evidence_values,
        interval_evidence="interval-certified" in evidence_values,
    )
