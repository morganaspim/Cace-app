import pytest

from cace_studio.core.claim_promotion import (
    ClaimEvidence,
    ClaimScope,
    ClaimStage,
    ExternalReviewAttestation,
    IndependentReproductionAttestation,
    evaluate_claim,
    fail_closed_module_decision,
    research_candidate_decision,
    unsafe_self_promotion_paths,
)
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Experiment, Node
from cace_studio.core.module import ValidationError
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.report import graph_certificate
from cace_studio.core.types import EvidenceKind, Maturity, ModuleMetadata, ProofStatus
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.modules.fem_v076 import proof_obligation_dag


CLAIM_DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def _formal_evidence(**updates):
    data = dict(
        unresolved_obligations=(),
        formal_kernel_verified=True,
        axiom_audit_passed=True,
        pinned_ci_passed=True,
        exact_statement_digest=CLAIM_DIGEST,
        independent_reproductions=0,
        reproduction_attestations=(),
        external_reviews=(),
    )
    data.update(updates)
    return ClaimEvidence(**data)


def _reproduction(digest=CLAIM_DIGEST):
    return IndependentReproductionAttestation(
        reproducer_identity="independent-reproducer",
        artifact_sha256=digest,
        decision="reproduced",
        independent=True,
        source="external",
    )


def _review(digest=CLAIM_DIGEST):
    return ExternalReviewAttestation(
        reviewer_identity="independent-reviewer",
        artifact_sha256=digest,
        decision="verified",
        independent=True,
        source="external",
    )


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


def test_malformed_exact_statement_digest_blocks_formal_gate():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(exact_statement_digest="not-a-sha256"),
    )
    assert d.stage is ClaimStage.RESEARCH_CANDIDATE
    assert "exact-statement-digest-invalid" in d.blockers


def test_formal_open_problem_proof_is_still_not_a_resolution_claim():
    d = evaluate_claim(ClaimScope.OPEN_PROBLEM_RESOLUTION, _formal_evidence())
    assert d.stage is ClaimStage.FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert "artifact-bound-independent-reproduction-missing" in d.blockers


def test_legacy_reproduction_count_is_not_enough():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(independent_reproductions=2),
    )
    assert d.stage is ClaimStage.FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert "legacy-reproduction-count-not-artifact-bound" in d.blockers


def test_mismatched_reproduction_artifact_does_not_promote():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(reproduction_attestations=(_reproduction(OTHER_DIGEST),)),
    )
    assert d.stage is ClaimStage.FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed


def test_matching_reproduction_reaches_reproduced_candidate_but_not_resolution():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(reproduction_attestations=(_reproduction(),)),
    )
    assert d.stage is ClaimStage.REPRODUCED_FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed
    assert d.blockers == ("artifact-bound-external-review-missing-or-invalid",)


def test_invalid_external_review_does_not_promote():
    review = ExternalReviewAttestation(
        reviewer_identity="reviewer",
        artifact_sha256="not-a-digest",
        decision="approve",
    )
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(
            reproduction_attestations=(_reproduction(),),
            external_reviews=(review,),
        ),
    )
    assert d.stage is ClaimStage.REPRODUCED_FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed


def test_review_of_different_artifact_does_not_promote():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(
            reproduction_attestations=(_reproduction(),),
            external_reviews=(_review(OTHER_DIGEST),),
        ),
    )
    assert d.stage is ClaimStage.REPRODUCED_FORMAL_CANDIDATE
    assert not d.public_resolution_claim_allowed


def test_matching_reproduction_and_review_are_required_for_resolution_wording():
    d = evaluate_claim(
        ClaimScope.OPEN_PROBLEM_RESOLUTION,
        _formal_evidence(
            reproduction_attestations=(_reproduction(),),
            external_reviews=(_review(),),
        ),
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


def test_existing_v076_reliability_dag_routes_through_global_guard():
    dag = proof_obligation_dag()
    assert dag["reliability_promotable"] is False
    d = research_candidate_decision(
        unresolved_obligations=dag["unresolved"],
        numerical_evidence=True,
        symbolic_evidence=True,
    )
    assert d.stage is ClaimStage.RESEARCH_CANDIDATE
    assert d.public_resolution_claim_allowed is False
    assert "unresolved-proof-obligations" in d.blockers


def test_framework_module_guard_ignores_self_asserted_promotion():
    proof = ProofStatus(evidence={EvidenceKind.NUMERICAL, EvidenceKind.SYMBOLIC})
    outputs = {
        "result": {
            "public_resolution_claim_allowed": True,
            "proof_obligation_dag": {"unresolved": ["trace_local", "density"]},
        }
    }
    d = fail_closed_module_decision("Reliability Theorem", proof, outputs)
    assert d is not None
    assert d.stage is ClaimStage.RESEARCH_CANDIDATE
    assert d.public_resolution_claim_allowed is False
    assert "unresolved-proof-obligations" in d.blockers
    assert unsafe_self_promotion_paths(outputs) == ("result.public_resolution_claim_allowed",)


def test_non_open_problem_category_has_no_forced_claim_decision():
    proof = ProofStatus(evidence={EvidenceKind.NUMERICAL})
    assert fail_closed_module_decision("Linear Algebra", proof, {"result": {"pass": True}}) is None


class _DummyOpenProblemModule(ResultModule):
    fn = staticmethod(lambda: {
        "pass": True,
        "blocking_nodes": ["unproved-density"],
    })
    module_id = "test.open_problem"
    label = "Open Problem Research Module"
    version = "0.0.1"
    description = "Test research module with unresolved obligations."
    evidence_kind = EvidenceKind.SYMBOLIC
    metadata = ModuleMetadata(
        module_id,
        label,
        version,
        "Reliability Theorem",
        description,
        Maturity.EXPERIMENTAL,
    )
    proof_status = ProofStatus(evidence={EvidenceKind.SYMBOLIC}, unit_tests=True)


class _DummyUnsafeOpenProblemModule(ResultModule):
    fn = staticmethod(lambda: {
        "pass": True,
        "public_resolution_claim_allowed": True,
        "blocking_nodes": ["unproved-density"],
    })
    module_id = "test.unsafe_open_problem"
    label = "Unsafe Open Problem Module"
    version = "0.0.1"
    description = "Test module that attempts reserved self-promotion."
    evidence_kind = EvidenceKind.SYMBOLIC
    metadata = ModuleMetadata(
        module_id,
        label,
        version,
        "Reliability Theorem",
        description,
        Maturity.EXPERIMENTAL,
    )
    proof_status = ProofStatus(evidence={EvidenceKind.SYMBOLIC}, unit_tests=True)


def test_executor_and_report_add_fail_closed_claim_sidecar():
    registry = ModuleRegistry()
    registry.register(_DummyOpenProblemModule)
    exp = Experiment(name="claim-guard", nodes=[Node(id="n1", module_id="test.open_problem")])
    result = GraphExecutor(registry).run(exp)
    decision = result.claim_decisions["n1"]
    assert decision["stage"] == "research-candidate"
    assert decision["public_resolution_claim_allowed"] is False
    assert result.any_public_resolution_claim_allowed is False
    cert = graph_certificate(result)
    assert cert["claim_decision_nodes"] == 1
    assert cert["public_resolution_claims_allowed"] == 0


def test_executor_rejects_reserved_public_self_promotion():
    registry = ModuleRegistry()
    registry.register(_DummyUnsafeOpenProblemModule)
    exp = Experiment(name="unsafe-claim", nodes=[Node(id="n1", module_id="test.unsafe_open_problem")])
    with pytest.raises(ValidationError, match="attempted reserved public promotion"):
        GraphExecutor(registry).run(exp)
