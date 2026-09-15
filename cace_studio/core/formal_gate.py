from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .claim_registry import ClaimRegistry
from .proof_contract import ProofContractRegistry
from .proof_ledger import ProofLedger
from .types import EvidenceKind
from .verification import VerificationRecord, VerificationState


def enforce_formal_claim_qualification(
    module_id: str,
    records: Iterable[VerificationRecord],
    *,
    registry: ClaimRegistry | None = None,
    ledger: ProofLedger | None = None,
    contracts: ProofContractRegistry | None = None,
) -> list[VerificationRecord]:
    """Fail closed for formal PASS records.

    FORMAL+PASS survives only when claim registry, proof contract and proof ledger
    agree on current-head, content-addressed qualification. Contract drift,
    missing required checks, or missing provenance downgrades the runtime record
    to NOT_RUN rather than inheriting stale proof status.
    """

    reg = registry or ClaimRegistry.load_default()
    proof_ledger = ledger or ProofLedger.load_default()
    proof_contracts = contracts or ProofContractRegistry.load_default()
    claim = reg.for_module(module_id)
    out: list[VerificationRecord] = []

    for record in records:
        if record.kind is not EvidenceKind.FORMAL or record.state is not VerificationState.PASS:
            out.append(record)
            continue

        if claim is None:
            out.append(
                replace(
                    record,
                    state=VerificationState.NOT_RUN,
                    method=f"{record.method}; claim-registry gate",
                    metrics={
                        **record.metrics,
                        "formal_gate": "NOT_RUN",
                        "formal_gate_reason": "claim-registry-entry-missing",
                        "claim_registry_sha256": reg.registry_sha256,
                        "proof_contract_registry_sha256": proof_contracts.registry_sha256,
                        "proof_ledger_sha256": proof_ledger.ledger_sha256,
                    },
                    notes=record.notes
                    + (
                        "Formal PASS downgraded to NOT_RUN: no canonical claim-registry "
                        f"entry is bound to module {module_id}.",
                    ),
                )
            )
            continue

        contract = (
            proof_contracts.by_id(claim.proof_contract_id)
            if claim.proof_contract_id
            else None
        )
        ledger_entry = proof_ledger.for_claim(claim.claim_id)
        blockers: list[str] = []

        if claim.qualification_status != "PASS":
            blockers.append("claim-registry-status-not-pass")
        if claim.evidence_ceiling not in {"formally-verified", "cross-verified"}:
            blockers.append("claim-registry-evidence-ceiling-below-formal")
        if not claim.current_head_qualified:
            blockers.append("claim-registry-current-head-qualification-missing")
        if not claim.proof_contract_id:
            blockers.append("claim-proof-contract-id-missing")
        if contract is None:
            blockers.append("proof-contract-missing")
        elif contract.claim_id != claim.claim_id:
            blockers.append("proof-contract-claim-mismatch")

        if ledger_entry is None:
            blockers.append("proof-ledger-entry-missing")
        else:
            if ledger_entry.status != "PASS":
                blockers.append("proof-ledger-status-not-pass")
            if not ledger_entry.current_head_qualified:
                blockers.append("proof-ledger-current-head-qualification-missing")
            if not ledger_entry.qualification_system:
                blockers.append("proof-ledger-qualification-system-missing")
            if not ledger_entry.qualification_run_id:
                blockers.append("proof-ledger-qualification-run-missing")
            if (
                ledger_entry.qualification_system == "github-actions"
                and (ledger_entry.workflow_run_id is None or ledger_entry.workflow_run_id <= 0)
            ):
                blockers.append("proof-ledger-workflow-run-missing")
            if not ledger_entry.checks:
                blockers.append("proof-ledger-qualification-checks-missing")
            if ledger_entry.blockers:
                blockers.append("proof-ledger-retains-blockers")
            if claim.proof_artifact_sha256 != ledger_entry.proof_artifact_sha256:
                blockers.append("proof-artifact-hash-mismatch")
            if claim.attested_commit != ledger_entry.commit:
                blockers.append("attested-commit-mismatch")
            if claim.proof_contract_id != ledger_entry.proof_contract_id:
                blockers.append("proof-contract-id-mismatch")
            if contract is not None:
                if ledger_entry.proof_contract_sha256 != contract.contract_sha256:
                    blockers.append("proof-contract-hash-mismatch")
                missing_checks = sorted(set(contract.required_checks) - set(ledger_entry.checks))
                if missing_checks:
                    blockers.append(
                        "proof-contract-required-checks-missing:" + ",".join(missing_checks)
                    )

        if blockers:
            reason = claim.reason or ",".join(blockers)
            out.append(
                replace(
                    record,
                    state=VerificationState.NOT_RUN,
                    method=f"{record.method}; claim-registry gate",
                    metrics={
                        **record.metrics,
                        "formal_gate": "NOT_RUN",
                        "formal_gate_reason": reason,
                        "formal_gate_blockers": tuple(blockers),
                        "claim_id": claim.claim_id,
                        "claim_registry_sha256": reg.registry_sha256,
                        "proof_contract_registry_sha256": proof_contracts.registry_sha256,
                        "proof_contract_id": claim.proof_contract_id,
                        "proof_contract_sha256": contract.contract_sha256 if contract else None,
                        "proof_ledger_sha256": proof_ledger.ledger_sha256,
                        "qualification_status": claim.qualification_status,
                        "attested_commit": claim.attested_commit,
                    },
                    notes=record.notes
                    + (
                        "Formal PASS downgraded to NOT_RUN because canonical claim, proof-contract, "
                        f"or proof-ledger qualification is incomplete for {claim.claim_id}.",
                    ),
                )
            )
            continue

        assert ledger_entry is not None and contract is not None
        provenance_metrics = {
            "qualification_system": ledger_entry.qualification_system,
            "qualification_run_id": ledger_entry.qualification_run_id,
        }
        if ledger_entry.workflow_run_id is not None:
            provenance_metrics["workflow_run_id"] = ledger_entry.workflow_run_id
        out.append(
            replace(
                record,
                metrics={
                    **record.metrics,
                    "formal_gate": "PASS",
                    "claim_id": claim.claim_id,
                    "claim_registry_sha256": reg.registry_sha256,
                    "proof_contract_registry_sha256": proof_contracts.registry_sha256,
                    "proof_contract_id": contract.contract_id,
                    "proof_contract_sha256": contract.contract_sha256,
                    "proof_ledger_sha256": proof_ledger.ledger_sha256,
                    "qualification_status": claim.qualification_status,
                    "attested_commit": ledger_entry.commit,
                    "proof_artifact_sha256": ledger_entry.proof_artifact_sha256,
                    **provenance_metrics,
                },
                notes=record.notes
                + (
                    f"Formal evidence bound to claim {claim.claim_id}, proof contract "
                    f"{contract.contract_id}@{contract.contract_sha256}, commit {ledger_entry.commit}, "
                    f"proof artifact {ledger_entry.proof_artifact_sha256}, and qualification "
                    f"{ledger_entry.qualification_system}:{ledger_entry.qualification_run_id}.",
                ),
            )
        )

    return out
