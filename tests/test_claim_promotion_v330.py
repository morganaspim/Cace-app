from cace_studio.core.claim_promotion import (
    ClaimDecision,
    ClaimEvidence,
    ClaimScope,
    ClaimStage,
    ExternalReviewAttestation,
    evaluate_claim,
    research_candidate_decision,
)


def _formal_evidence(**updates):
    data = dict(
        unresolved_obligations=(),
        formal_kernel_verified=True,
        axiom_audit_passed=True,
        pinned_ci_passed=True,
        exact_statement_digest="a" * 64,
        independent_reproductions=0,
        external_reviews=(),
    )
    data.update(updates)
    return ClaimEvidence(**data)


def test_numerical_or_symbolic_evidence_never_promotes_open_problem():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        ClaimEvidence(numerical_evidence=True, symbolic_evidence=True, interval_evidence=True),
    )
    assert d.stage is ClaimStage.RESEARCH_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert "formal-kernel-verification-missing" in d.blockers


def test_unresolved_obligation_blocks_even_if_other_formal_flags_are_true():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(unresolved_obligations=("graph-norm-density",)),
    )
    assert d.stage is ClaimStage.RESEARCH_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert "unresolved-proof-obligations" in d.blockers


def test_formal_open_problem_proof_is_still_not_a_resolution_claim():
    d = evaluate_claim(ClaimScope.OPEN_PROBLEM_RESOLUTION, _formal_evidence())
    assert d.stage is ClaimStage.FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert set(d.blockers) == {"independent-reproduction-missing", "external-review-missing"}


def test_reproduced_formal_candidate_still_requires_external_review():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(independent_reproductions=1),
    )
    assert d.stage is ClaimStage.REPRODUCED_FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert d.blockers == ("external-review-missing-or-invalid",)


def test_invalid_external_review_does_not_promote():
    review = ExternalReviewAttestation(
        reviewer_identity="reviewer",
        artifact_sha256="not-a-digest",
        decision="approve",
    )
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(independent_reproductions=1, external_reviews=(review,)),
    )
    assert d.stage is ClaimStage.REPRODUCED_FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed


def test_valid_external_review_is_required_for_resolution_wording():
    review = ExternalReviewAttestation(
        reviewer_identity="independent-reviewer",
        artifact_sha256="b" * 64,
        decision="verified",
        independent=True,
        source="external",
    )
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(independent_reproductions=1, external_reviews=(review,)),
    )
    assert d.stage is ClaimStage.EXTERNALLY_REVIEWED_RESOLUTION
    assert d.public_resolution_claim_allowed
    assert d.blockers == ()
    assert any("external trust boundary" in x for x in d.trust_boundary)


def test_reliability_discovery_helper_is_fail_closed():
    d = research_candidate_decision(
        unresolved_obligations=("trace_local", "residual_representation"),
        numerical_evidence=True,
        symbolic_evidence=True,
    )
    payload = d.to_dict()
    assert payload["stage"] == "research-candidate"
    assert payload["public_resolution_claim_allowed"] is False
    assert "unresolved-proof-obligations" in payload["blockers"]
