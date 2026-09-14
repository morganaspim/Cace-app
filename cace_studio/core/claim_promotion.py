from __future__ import annotations

"""Repository-wide evidence and claim-promotion policy.

The purpose of this module is deliberately conservative: computational evidence may suggest a
conjecture, and Lean may certify a formal statement, but CACE must not silently collapse those
very different states into the word "solved".

In particular, an open-problem-resolution claim is never public-claim eligible from CACE's own
numerical, symbolic, interval, or formal output alone.  It additionally needs independent
reproduction and a recorded external review attestation.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable


class ClaimScope(str, Enum):
    ORDINARY = "ordinary"
    OPEN_PROBLEM_RESOLUTION = "open-problem-resolution"


class ClaimStage(str, Enum):
    RESEARCH_CANDIDATE = "research-candidate"
    FORMAL_CANDIDATE = "formal-candidate"
    REPRODUCED_FORMAL_CANDIDATE = "reproduced-formal-candidate"
    EXTERNALLY_REVIEWED_RESOLUTION = "externally-reviewed-resolution"


@dataclass(frozen=True)
class ExternalReviewAttestation:
    """A record supplied from outside the theorem-producing CACE run.

    `artifact_sha256` binds the review to a concrete manuscript/proof artifact.  This dataclass does
    not pretend to establish the human reviewer's identity cryptographically; that remains an
    external trust boundary and is reported as such.
    """

    reviewer_identity: str
    artifact_sha256: str
    decision: str
    independent: bool = True
    source: str = "external"

    def valid_for_promotion(self) -> bool:
        digest = self.artifact_sha256.lower()
        return (
            self.source == "external"
            and self.independent
            and bool(self.reviewer_identity.strip())
            and self.decision.lower() in {"approve", "accepted", "verified"}
            and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest)
        )


@dataclass(frozen=True)
class ClaimEvidence:
    unresolved_obligations: tuple[str, ...] = ()
    formal_kernel_verified: bool = False
    axiom_audit_passed: bool = False
    pinned_ci_passed: bool = False
    exact_statement_digest: str | None = None
    independent_reproductions: int = 0
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

    def to_dict(self) -> dict:
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
    if not evidence.exact_statement_digest:
        blockers.append("exact-statement-digest-missing")
    return not blockers, blockers


def evaluate_claim(scope: ClaimScope, evidence: ClaimEvidence) -> ClaimDecision:
    """Evaluate the strongest wording CACE is permitted to use for a claim.

    This is fail-closed.  Numerical/symbolic/interval evidence cannot substitute for the formal
    gate.  For an open-problem resolution, even a fully kernel-checked theorem remains only a
    formal candidate until it has an independent reproduction and external review.
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

    if evidence.independent_reproductions < 1:
        return ClaimDecision(
            scope=scope,
            stage=ClaimStage.FORMAL_CANDIDATE,
            public_resolution_claim_allowed=False,
            blockers=("independent-reproduction-missing", "external-review-missing"),
            trust_boundary=tuple(trust_boundary),
        )

    valid_reviews = tuple(r for r in evidence.external_reviews if r.valid_for_promotion())
    trust_boundary.append("independent reproduction provenance")
    if not valid_reviews:
        return ClaimDecision(
            scope=scope,
            stage=ClaimStage.REPRODUCED_FORMAL_CANDIDATE,
            public_resolution_claim_allowed=False,
            blockers=("external-review-missing-or-invalid",),
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
