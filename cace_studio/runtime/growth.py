from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from typing import Any, Protocol

from .hashing import stable_hash


class GrowthMode(str, Enum):
    SUGGESTIONS_ONLY = "SUGGESTIONS_ONLY"
    TEST_IN_ISOLATION = "TEST_IN_ISOLATION"
    AUTONOMOUS = "AUTONOMOUS"


class GrowthBlocked(RuntimeError):
    pass


class ProposalEngine(Protocol):
    def propose(self, observation: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class GrowthPrerequisites:
    proof_kernel_locked: bool
    strict_sandbox_available: bool
    airlock_enabled: bool
    entitlement_allowed: bool
    heartbeat_enabled: bool
    hash_bounded_propagation_enabled: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.proof_kernel_locked,
                self.strict_sandbox_available,
                self.airlock_enabled,
                self.entitlement_allowed,
                self.heartbeat_enabled,
                self.hash_bounded_propagation_enabled,
            )
        )


@dataclass(frozen=True)
class GrowthCandidate:
    proposal: dict[str, Any]
    proposal_sha256: str
    evidence_status: str = "RESEARCH_CANDIDATE"
    may_promote_formal_evidence: bool = False


class GrowthController:
    """Fail-closed controller for the paper's future VAE/self-growing stage.

    The controller can accept a VAE-like proposal engine, but candidates remain
    RESEARCH_CANDIDATE until separate numerical/formal gates run. Even in
    AUTONOMOUS mode, import to the primary graph requires an Airlock approval.
    """

    def __init__(
        self,
        *,
        mode: GrowthMode,
        prerequisites: GrowthPrerequisites,
        max_nodes: int = 256,
        max_generations: int = 64,
    ) -> None:
        self.mode = mode
        self.prerequisites = prerequisites
        self.max_nodes = max_nodes
        self.max_generations = max_generations
        self._seen_hashes: set[str] = set()
        self._generation = 0

    def assert_enabled(self) -> None:
        if self.mode is GrowthMode.SUGGESTIONS_ONLY:
            return
        if not self.prerequisites.passed:
            raise GrowthBlocked("growth prerequisites are not all satisfied")
        if self.mode is GrowthMode.AUTONOMOUS and os.environ.get("CACE_ENABLE_AUTONOMOUS_GROWTH") != "1":
            raise GrowthBlocked("autonomous VAE growth is disabled by default")

    def next_candidate(self, engine: ProposalEngine, observation: dict[str, Any]) -> GrowthCandidate:
        self.assert_enabled()
        if self._generation >= self.max_generations:
            raise GrowthBlocked("growth generation limit reached")
        proposal = engine.propose(observation)
        if not isinstance(proposal, dict):
            raise GrowthBlocked("proposal engine returned a non-object proposal")
        nodes = proposal.get("nodes", [])
        if isinstance(nodes, list) and len(nodes) > self.max_nodes:
            raise GrowthBlocked("watchdog rejected node explosion")
        digest = stable_hash(proposal, algorithm="sha256")
        if digest in self._seen_hashes:
            raise GrowthBlocked("watchdog detected repeated/oscillating proposal hash")
        self._seen_hashes.add(digest)
        self._generation += 1
        return GrowthCandidate(proposal=proposal, proposal_sha256=digest)

    @staticmethod
    def authorize_import(
        candidate: GrowthCandidate,
        *,
        rigor_gate_passed: bool,
        airlock_manifest_sha256: str,
        approved_manifest_sha256: str,
        reviewer: str,
    ) -> dict[str, Any]:
        if not rigor_gate_passed:
            raise GrowthBlocked("candidate failed rigor gate")
        if not reviewer.strip():
            raise GrowthBlocked("human Airlock reviewer is required")
        if airlock_manifest_sha256 != approved_manifest_sha256:
            raise GrowthBlocked("human approval does not match exact Airlock manifest")
        return {
            "schema": "cace-growth-import-authorization-v1",
            "candidate_sha256": candidate.proposal_sha256,
            "airlock_manifest_sha256": airlock_manifest_sha256,
            "reviewer": reviewer.strip(),
            "evidence_status": candidate.evidence_status,
            "formal_promotion": False,
        }
