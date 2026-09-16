from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .claim_registry import ClaimEntry, ClaimRegistry
from .proof_contract import ProofContract, ProofContractRegistry
from .proof_ledger import ProofLedger, ProofLedgerEntry
from .qualification_attestation import VerifiedQualification
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
    proof_contract_id: str | None
    proof_contract_sha256: str | None
    proof_contract_build_target: str | None
    endpoint_theorems: tuple[str, ...]
    audited_source_files: tuple[str, ...]
    allowed_axioms: tuple[str, ...]
    required_checks: tuple[str, ...]
    theorem_dependency_metadata_state: str
    theorem_dependency_metadata_note: str
    ledger_release: str | None
    ledger_status: str | None
    qualification_state: str
    qualification_source: str
    current_head_qualified: bool
    attested_commit: str | None
    proof_artifact_sha256: str | None
    qualification_system: str | None
    qualification_run_id: str | None
    workflow_run_id: int | None
    checks: tuple[str, ...]
    blockers: tuple[str, ...]
    nonclaims: tuple[str, ...]
    contract_nonclaims: tuple[str, ...]
    runtime_evidence: tuple[RuntimeEvidenceView, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["runtime_evidence"] = [asdict(item) for item in self.runtime_evidence]
        return payload


def _qualification_state(
    claim: ClaimEntry,
    ledger: ProofLedgerEntry | None,
    contract: ProofContract | None,
    external: VerifiedQualification | None = None,
) -> tuple[str, bool, tuple[str, ...], str]:
    conflicts: list[str] = []
    blockers: list[str] = []

    if claim.proof_contract_id:
        if contract is None:
            conflicts.append("Claim references a proof contract missing from the canonical registry.")
        elif contract.contract_id != claim.proof_contract_id or contract.claim_id != claim.claim_id:
            conflicts.append("Claim and proof contract disagree on canonical binding.")
    elif claim.current_head_qualified:
        conflicts.append("Current-head formal qualification is missing a proof-contract binding.")

    if ledger is None:
        blockers.append("No canonical proof-ledger entry is bound to this claim.")
        if claim.current_head_qualified:
            conflicts.append("Registry marks current-head qualified but the proof ledger has no entry.")
        if external is not None:
            conflicts.append(
                "External qualification cannot apply without a canonical proof-ledger entry."
            )
    else:
        if claim.current_head_qualified != ledger.current_head_qualified:
            conflicts.append("Registry and proof ledger disagree about current-head qualification.")
        if claim.proof_contract_id and ledger.proof_contract_id:
            if claim.proof_contract_id != ledger.proof_contract_id:
                conflicts.append("Claim and proof ledger disagree on proof-contract ID.")
        if contract is not None and ledger.proof_contract_sha256 is not None:
            if contract.contract_sha256 != ledger.proof_contract_sha256:
                conflicts.append("Proof ledger is bound to a different proof-contract SHA-256.")
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
            if contract is None:
                conflicts.append("Current-head qualification has no canonical proof contract.")
            else:
                if ledger.proof_contract_id != contract.contract_id:
                    conflicts.append("Qualified ledger proof-contract ID does not match current contract.")
                if ledger.proof_contract_sha256 != contract.contract_sha256:
                    conflicts.append("Qualified ledger proof-contract hash does not match current contract.")
                missing = sorted(set(contract.required_checks) - set(ledger.checks))
                if missing:
                    conflicts.append(
                        "Qualified ledger is missing contract-required checks: " + ", ".join(missing)
                    )
        blockers.extend(ledger.blockers)

    if external is not None:
        if contract is None:
            conflicts.append("External qualification has no canonical proof contract.")
        else:
            if external.claim_id != claim.claim_id:
                conflicts.append("External qualification is bound to a different claim.")
            if external.proof_contract_id != contract.contract_id:
                conflicts.append("External qualification proof-contract ID does not match.")
            if external.proof_contract_sha256 != contract.contract_sha256:
                conflicts.append("External qualification proof-contract SHA-256 does not match.")
            if external.endpoint_theorems != contract.endpoint_theorems:
                conflicts.append("External qualification endpoint set does not match.")
            if external.checks != contract.required_checks:
                conflicts.append("External qualification required-check set does not match.")
        if claim.current_head_qualified:
            if claim.attested_commit != external.git_commit:
                conflicts.append("Registry attested commit disagrees with external qualification.")
            if claim.proof_artifact_sha256 != external.proof_artifact_sha256:
                conflicts.append("Registry artifact digest disagrees with external qualification.")
        if ledger is not None and ledger.current_head_qualified:
            if ledger.commit != external.git_commit:
                conflicts.append("Proof ledger commit disagrees with external qualification.")
            if ledger.proof_artifact_sha256 != external.proof_artifact_sha256:
                conflicts.append("Proof ledger artifact digest disagrees with external qualification.")

    if claim.reason:
        blockers.append(claim.reason)

    if conflicts:
        return "CONFLICT", False, tuple(dict.fromkeys(conflicts + blockers)), "conflict"

    if external is not None:
        return "QUALIFIED", True, tuple(), external.source

    exact_qualified = bool(
        ledger is not None
        and contract is not None
        and claim.current_head_qualified
        and ledger.current_head_qualified
        and claim.qualification_status == "PASS"
        and ledger.status == "PASS"
        and claim.attested_commit == ledger.commit
        and claim.proof_artifact_sha256 == ledger.proof_artifact_sha256
        and claim.proof_contract_id == contract.contract_id == ledger.proof_contract_id
        and ledger.proof_contract_sha256 == contract.contract_sha256
        and set(contract.required_checks).issubset(ledger.checks)
        and bool(claim.attested_commit)
        and bool(claim.proof_artifact_sha256)
    )
    if exact_qualified:
        return "QUALIFIED", True, tuple(), "canonical-static"
    return "UNQUALIFIED", False, tuple(dict.fromkeys(blockers)), "canonical-static"


class ProofExplorer:
    """Read-only claim -> proof contract -> ledger -> exact qualification view."""

    def __init__(
        self,
        registry: ClaimRegistry | None = None,
        ledger: ProofLedger | None = None,
        contracts: ProofContractRegistry | None = None,
        qualifications: Iterable[VerifiedQualification] = (),
    ) -> None:
        self.registry = registry or ClaimRegistry.load_default()
        self.ledger = ledger or ProofLedger.load_default()
        self.contracts = contracts or ProofContractRegistry.load_default()
        indexed: dict[str, VerifiedQualification] = {}
        for qualification in qualifications:
            if qualification.claim_id in indexed:
                raise ValueError(
                    f"duplicate external qualification for claim {qualification.claim_id!r}"
                )
            indexed[qualification.claim_id] = qualification
        self.qualifications = indexed

    def claim_view(
        self,
        claim_id: str,
        runtime_records: Iterable[VerificationRecord] = (),
    ) -> ProofClaimView:
        claim = self.registry.by_id(claim_id)
        if claim is None:
            raise KeyError(f"unknown canonical claim_id: {claim_id}")
        ledger = self.ledger.for_claim(claim_id)
        contract = (
            self.contracts.by_id(claim.proof_contract_id)
            if claim.proof_contract_id
            else None
        )
        external = self.qualifications.get(claim_id)
        state, qualified, derived_blockers, source = _qualification_state(
            claim, ledger, contract, external
        )
        runtime = tuple(
            RuntimeEvidenceView.from_record(record, claim_id)
            for record in runtime_records
        )
        attested_commit = external.git_commit if external is not None and qualified else claim.attested_commit
        artifact_sha = (
            external.proof_artifact_sha256
            if external is not None and qualified
            else claim.proof_artifact_sha256
        )
        qualification_system = (
            external.qualification_system
            if external is not None and qualified
            else (ledger.qualification_system if ledger else None)
        )
        qualification_run_id = (
            external.qualification_run_id
            if external is not None and qualified
            else (ledger.qualification_run_id if ledger else None)
        )
        workflow_run_id = (
            external.workflow_run_id
            if external is not None and qualified
            else (ledger.workflow_run_id if ledger else None)
        )
        checks = (
            external.checks
            if external is not None and qualified
            else (ledger.checks if ledger else ())
        )
        return ProofClaimView(
            claim_id=claim.claim_id,
            statement=claim.statement,
            scope=claim.scope,
            evidence_ceiling=claim.evidence_ceiling,
            registry_status=claim.qualification_status,
            proof_contract_id=contract.contract_id if contract else claim.proof_contract_id,
            proof_contract_sha256=contract.contract_sha256 if contract else None,
            proof_contract_build_target=contract.build_target if contract else None,
            endpoint_theorems=contract.endpoint_theorems if contract else (),
            audited_source_files=contract.audited_source_files if contract else (),
            allowed_axioms=contract.allowed_axioms if contract else (),
            required_checks=contract.required_checks if contract else (),
            theorem_dependency_metadata_state=(
                contract.theorem_dependency_metadata_state if contract else "UNAVAILABLE"
            ),
            theorem_dependency_metadata_note=(
                contract.theorem_dependency_metadata_note
                if contract
                else "No proof contract is bound to this claim."
            ),
            ledger_release=ledger.release if ledger else None,
            ledger_status=ledger.status if ledger else None,
            qualification_state=state,
            qualification_source=source,
            current_head_qualified=qualified,
            attested_commit=attested_commit,
            proof_artifact_sha256=artifact_sha,
            qualification_system=qualification_system,
            qualification_run_id=qualification_run_id,
            workflow_run_id=workflow_run_id,
            checks=checks,
            blockers=derived_blockers,
            nonclaims=claim.nonclaims,
            contract_nonclaims=contract.nonclaims if contract else (),
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
