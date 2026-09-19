from __future__ import annotations

from cace_studio.ai.capability_gate import (
    AICapabilityManifest,
    AICapabilityPolicy,
    CapabilityTier,
)


def test_superintelligence_class_is_denied_by_default():
    manifest = AICapabilityManifest("future", "model", CapabilityTier.SUPERINTELLIGENCE_CLASS)
    decision = AICapabilityPolicy().admit(manifest)
    assert decision.allowed is False
    assert any("disabled" in reason for reason in decision.reasons)


def test_enabling_tier_does_not_enable_network_or_self_modification():
    policy = AICapabilityPolicy(allow_superintelligence_class=True)
    manifest = AICapabilityManifest(
        "future",
        "model",
        CapabilityTier.SUPERINTELLIGENCE_CLASS,
        requests_network=True,
        requests_self_modification=True,
    )
    decision = policy.admit(manifest)
    assert decision.allowed is False
    assert any("network" in reason for reason in decision.reasons)
    assert any("self-modification" in reason for reason in decision.reasons)


def test_ai_evidence_mutation_is_always_denied():
    policy = AICapabilityPolicy(
        allow_superintelligence_class=True,
        allow_network=True,
        allow_self_modification=True,
        allow_worker_spawn=True,
    )
    manifest = AICapabilityManifest(
        "x", "y", CapabilityTier.BOUNDED, requests_evidence_mutation=True
    )
    assert policy.admit(manifest).allowed is False


def test_policy_description_does_not_claim_to_detect_intelligence():
    assert "not a mathematical detector" in AICapabilityPolicy().interpretation
