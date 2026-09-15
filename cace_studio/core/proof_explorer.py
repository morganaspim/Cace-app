from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .claim_registry import ClaimEntry, ClaimRegistry
from .proof_ledger import ProofLedger, ProofLedgerEntry
from .verification import VerificationRecord


@dataclass(frozen=True)
class RuntimeEvidenceView:
    verifier: str
    kind: str
    state: str
    claim: str
    method: str
    artifact_sha256: str
    canonical_claim_bound: bool

    @classmethod
    def from_record(cls, record: VerificationRecord, claim_id: str) -> "RuntimeEvidenceView":
        bound_id = str(record.metrics.get("claim_id", "")).strip()
        return cls(
            verifier=record.verifier,
            kind=record.kind.value,
            state=record.state.value,
            claim=record.claim,
            method=record.method,
            artifact_sha256=record.artifact_hash(),
            canonical_claim_bound=bound_id == claim_id,
        )


@dataclass(frozen=True)
class ProofClaimView:
    claim_id: str
    statement: str
    scope: str
    evidence_ceiling: str
    registry_status: str
    ledger_release: str | None
    ledger_status: str | None
    qualification_state: str
    current_head_qualified: bool
    attested_commit: str | None
    proof_artifact_sha256: str | None
    workflow_run_id: int | None
    checks: tuple[str, ...]
    blockers: tuple[str, ...]
    nonclaims: tuple[str, ...]
    runtime_evidence: tuple[RuntimeEvidenceView, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["runtime_evidence"] = [asdict(item) for item in self.runtime_evidence]
        return payload


def _qualification_state(
    claim: ClaimEntry, ledger: ProofLedgerEntry | None
) -> tuple[str, bool, tuple[str, ...]]:
    conflicts: list[str] = []
    blockers: list[str] = []

    if ledger is None:
        blockers.append("No canonical proof-ledger entry is bound to this claim.")
        if claim.current_head_qualified:
            conflicts.append("Registry marks current-head qualified but the proof ledger has no entry.")
    else:
        if claim.current_head_qualified != ledger.current_head_qualified:
            conflicts.append(
                "Registry and proof ledger disagree about current-head qualification."
            )
        if claim.current_head_qualified or ledger.current_head_qualified:
            if claim.qualification_status != "PASS":
                conflicts.append("Registry current-head qualification is not status PASS.")
            if ledger.status != "PASS":
                conflicts.append("Proof-ledger current-head qualification is not status PASS.")
            if claim.attested_commit != ledger.commit:
                conflicts.append("Registry and proof ledger disagree on attested commit.")
            if claim.proof_artifact_sha256 != ledger.proof_artifact_sha256:
                conflicts.append("Registry and proof ledger disagree on proof artifact SHA-256.")
            if not claim.attested_commit or not claim.proof_artifact_sha256:
                conflicts.append("Current-head qualification is missing content-addressed proof metadata.")

        blockers.extend(ledger.blockers)

    if claim.reason:
        blockers.append(claim.reason)

    if conflicts:
        return "CONFLICT", False, tuple(dict.fromkeys(conflicts + blockers))

    exact_qualified = bool(
        ledger is not None
        and claim.current_head_qualified
        and ledger.current_head_qualified
        and claim.qualification_status == "PASS"
        and ledger.status == "PASS"
        and claim.attested_commit == ledger.commit
        and claim.proof_artifact_sha256 == ledger.proof_artifact_sha256
        and bool(claim.attested_commit)
        and bool(claim.proof_artifact_sha256)
    )
    if exact_qualified:
        return "QUALIFIED", True, tuple()
    return "UNQUALIFIED", False, tuple(dict.fromkeys(blockers))


class ProofExplorer:
    """Read-only evidence view over the canonical claim registry and proof ledger.

    This class never promotes evidence. It only displays the state already
    authorized by the canonical registries and keeps runtime verification
    records separate from release qualification.
    """

    def __init__(
        self,
        registry: ClaimRegistry | None = None,
        ledger: ProofLedger | None = None,
    ) -> None:
        self.registry = registry or ClaimRegistry.load_default()
        self.ledger = ledger or ProofLedger.load_default()

    def claim_view(
        self,
        claim_id: str,
        runtime_records: Iterable[VerificationRecord] = (),
    ) -> ProofClaimView:
        claim = self.registry.by_id(claim_id)
        if claim is None:
            raise KeyError(f"unknown canonical claim_id: {claim_id}")
        ledger = self.ledger.for_claim(claim_id)
        state, qualified, derived_blockers = _qualification_state(claim, ledger)
        runtime = tuple(
            RuntimeEvidenceView.from_record(record, claim_id)
            for record in runtime_records
        )
        return ProofClaimView(
            claim_id=claim.claim_id,
            statement=claim.statement,
            scope=claim.scope,
            evidence_ceiling=claim.evidence_ceiling,
            registry_status=claim.qualification_status,
            ledger_release=ledger.release if ledger else None,
            ledger_status=ledger.status if ledger else None,
            qualification_state=state,
            current_head_qualified=qualified,
            attested_commit=claim.attested_commit,
            proof_artifact_sha256=claim.proof_artifact_sha256,
            workflow_run_id=ledger.workflow_run_id if ledger else None,
            checks=ledger.checks if ledger else (),
            blockers=derived_blockers,
            nonclaims=claim.nonclaims,
            runtime_evidence=runtime,
        )

    def for_module(
        self,
        module_id: str,
        *,
        formal_artifact: str | None = None,
        runtime_records: Iterable[VerificationRecord] = (),
    ) -> ProofClaimView | None:
        claim = self.registry.for_module(module_id)
        if claim is None and formal_artifact:
            claim = self.registry.by_id(formal_artifact)
        if claim is None:
            return None
        return self.claim_view(claim.claim_id, runtime_records)

    def all_claims(self) -> tuple[ProofClaimView, ...]:
        return tuple(self.claim_view(claim.claim_id) for claim in self.registry.claims)
