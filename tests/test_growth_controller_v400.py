import pytest

from cace_studio.runtime.growth import (
    GrowthBlocked,
    GrowthController,
    GrowthMode,
    GrowthPrerequisites,
)


class FakeVae:
    def __init__(self, proposal):
        self.proposal = proposal

    def propose(self, observation):
        return self.proposal


def _prereqs(**changes):
    values = dict(
        proof_kernel_locked=True,
        strict_sandbox_available=True,
        airlock_enabled=True,
        entitlement_allowed=True,
        heartbeat_enabled=True,
        hash_bounded_propagation_enabled=True,
    )
    values.update(changes)
    return GrowthPrerequisites(**values)


def test_autonomous_growth_is_disabled_by_default_even_when_prereqs_pass(monkeypatch):
    monkeypatch.delenv("CACE_ENABLE_AUTONOMOUS_GROWTH", raising=False)
    controller = GrowthController(mode=GrowthMode.AUTONOMOUS, prerequisites=_prereqs())
    with pytest.raises(GrowthBlocked, match="disabled by default"):
        controller.next_candidate(FakeVae({"nodes": []}), {})


def test_growth_watchdog_rejects_repeated_candidate_hash(monkeypatch):
    controller = GrowthController(mode=GrowthMode.TEST_IN_ISOLATION, prerequisites=_prereqs())
    engine = FakeVae({"nodes": [{"id": "n1"}]})
    first = controller.next_candidate(engine, {})
    assert first.evidence_status == "RESEARCH_CANDIDATE"
    assert first.may_promote_formal_evidence is False
    with pytest.raises(GrowthBlocked, match="repeated/oscillating"):
        controller.next_candidate(engine, {})


def test_airlock_and_rigor_gate_are_both_required_for_import():
    controller = GrowthController(mode=GrowthMode.SUGGESTIONS_ONLY, prerequisites=_prereqs())
    candidate = controller.next_candidate(FakeVae({"nodes": []}), {})
    with pytest.raises(GrowthBlocked):
        controller.authorize_import(
            candidate,
            rigor_gate_passed=False,
            airlock_manifest_sha256="a" * 64,
            approved_manifest_sha256="a" * 64,
            reviewer="human",
        )
    authorization = controller.authorize_import(
        candidate,
        rigor_gate_passed=True,
        airlock_manifest_sha256="a" * 64,
        approved_manifest_sha256="a" * 64,
        reviewer="human",
    )
    assert authorization["formal_promotion"] is False
