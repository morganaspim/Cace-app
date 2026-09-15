from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from .attestation import SignedAttestation, verify_attestation
from .claim_registry import ClaimRegistry
from .proof_contract import ProofContractRegistry
from .proof_ledger import ProofLedger

E5_STATUS = "E5-CROSS-VERIFIED"
PROOF_EFFECT = "none"


@dataclass(frozen=True)
class CrossVerificationResult:
    claim_id: str
    bundle_sha256: str
    qualified_commit: str | None
    proof_contract_id: str | None
    proof_contract_sha256: str | None
    eligible: bool
    status: str
    verifier_ids: tuple[str, ...]
    verifier_key_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    proof_effect: str = PROOF_EFFECT

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_e5(
    claim_id: str,
    bundle_sha256: str,
    attestations: Iterable[SignedAttestation],
    approved_keys: Mapping[str, str],
    *,
    registry: ClaimRegistry | None = None,
    ledger: ProofLedger | None = None,
    contracts: ProofContractRegistry | None = None,
    minimum_independent_verifiers: int = 2,
) -> CrossVerificationResult:
    """Evaluate E5 over an already-qualified, contract-bound canonical claim.

    E5 never creates proof. Contract drift invalidates E5 eligibility even when
    old signatures and proof-artifact hashes are otherwise internally valid.
    """
    if minimum_independent_verifiers < 2:
        raise ValueError("E5 requires at least two independent verifiers")
    registry = registry or ClaimRegistry.load_default()
    ledger = ledger or ProofLedger.load_default()
    contracts = contracts or ProofContractRegistry.load_default()
    claim = registry.by_id(claim_id)

    reasons: list[str] = []
    qualified_commit: str | None = None
    contract_id: str | None = None
    contract_sha256: str | None = None
    contract = None

    if claim is None:
        reasons.append("claim_id is not present in the canonical claim registry")
    else:
        qualified_commit = claim.attested_commit
        contract_id = claim.proof_contract_id
        contract = contracts.by_id(contract_id) if contract_id else None
        if contract is None:
            reasons.append("canonical claim has no resolvable proof contract")
        else:
            contract_sha256 = contract.contract_sha256
            if contract.claim_id != claim_id:
                reasons.append("proof contract is bound to a different claim")
        entry = ledger.for_claim(claim_id)
        if not claim.current_head_qualified or claim.qualification_status != "PASS":
            reasons.append("canonical claim is not current-head PASS qualified")
        if entry is None:
            reasons.append("canonical proof ledger has no entry for claim")
        else:
            if not entry.current_head_qualified or entry.status != "PASS":
                reasons.append("canonical proof-ledger entry is not current-head PASS qualified")
            if entry.commit != claim.attested_commit:
                reasons.append("registry and proof ledger disagree on qualified commit")
            if entry.proof_artifact_sha256 != claim.proof_artifact_sha256:
                reasons.append("registry and proof ledger disagree on proof artifact SHA-256")
            if entry.proof_contract_id != contract_id:
                reasons.append("registry and proof ledger disagree on proof-contract ID")
            if contract is not None and entry.proof_contract_sha256 != contract.contract_sha256:
                reasons.append("proof ledger is bound to a stale/different proof-contract hash")
            if contract is not None:
                missing_checks = sorted(set(contract.required_checks) - set(entry.checks))
                if missing_checks:
                    reasons.append(
                        "proof ledger is missing contract-required checks: " + ", ".join(missing_checks)
                    )
        if not claim.attested_commit or not claim.proof_artifact_sha256:
            reasons.append("canonical qualification is missing artifact-bound proof metadata")

    valid_verifiers: dict[str, str] = {}
    seen_statement_ids: set[str] = set()

    for attestation in attestations:
        try:
            actual_key_id = verify_attestation(attestation)
        except Exception as exc:
            reasons.append(f"invalid signed attestation: {type(exc).__name__}: {exc}")
            continue

        statement = attestation.statement
        if statement.statement_sha256 in seen_statement_ids:
            reasons.append(
                f"duplicate attestation statement ignored: {statement.statement_sha256}"
            )
            continue
        seen_statement_ids.add(statement.statement_sha256)

        if statement.purpose != "independent-reproduction":
            reasons.append(
                f"{statement.verifier_id}: attestation purpose is not independent-reproduction"
            )
            continue
        if statement.claim_id != claim_id:
            reasons.append(f"{statement.verifier_id}: claim_id does not match requested claim")
            continue
        if statement.bundle_sha256 != bundle_sha256:
            reasons.append(f"{statement.verifier_id}: bundle SHA-256 does not match")
            continue

        approved_verifier = approved_keys.get(actual_key_id)
        if approved_verifier is None:
            reasons.append(f"{statement.verifier_id}: verifier key is not approved")
            continue
        if approved_verifier != statement.verifier_id:
            reasons.append(
                f"{statement.verifier_id}: approved key is bound to a different verifier identity"
            )
            continue

        if (
            claim is None
            or contract is None
            or not claim.attested_commit
            or not claim.proof_artifact_sha256
        ):
            continue
        if statement.bindings.get("qualified_commit") != claim.attested_commit:
            reasons.append(
                f"{statement.verifier_id}: attestation is not bound to the qualified commit"
            )
            continue
        if statement.bindings.get("proof_artifact_sha256") != claim.proof_artifact_sha256:
            reasons.append(
                f"{statement.verifier_id}: attestation is not bound to the qualified proof artifact"
            )
            continue
        if statement.bindings.get("proof_contract_id") != contract.contract_id:
            reasons.append(
                f"{statement.verifier_id}: attestation is not bound to the qualified proof contract"
            )
            continue
        if statement.bindings.get("proof_contract_sha256") != contract.contract_sha256:
            reasons.append(
                f"{statement.verifier_id}: attestation is not bound to the current proof-contract hash"
            )
            continue

        prior_key = valid_verifiers.get(statement.verifier_id)
        if prior_key is not None and prior_key != actual_key_id:
            reasons.append(
                f"{statement.verifier_id}: multiple approved keys do not count as independent verifiers"
            )
            continue
        valid_verifiers[statement.verifier_id] = actual_key_id

    distinct_keys = set(valid_verifiers.values())
    if len(valid_verifiers) < minimum_independent_verifiers:
        reasons.append(
            f"need at least {minimum_independent_verifiers} distinct approved verifier identities"
        )
    if len(distinct_keys) < minimum_independent_verifiers:
        reasons.append(
            f"need at least {minimum_independent_verifiers} distinct approved verifier keys"
        )

    reasons = list(dict.fromkeys(reasons))
    eligible = not reasons
    return CrossVerificationResult(
        claim_id=claim_id,
        bundle_sha256=bundle_sha256,
        qualified_commit=qualified_commit,
        proof_contract_id=contract_id,
        proof_contract_sha256=contract_sha256,
        eligible=eligible,
        status=E5_STATUS if eligible else "E5-NOT-ELIGIBLE",
        verifier_ids=tuple(sorted(valid_verifiers)),
        verifier_key_ids=tuple(sorted(distinct_keys)),
        reasons=tuple(reasons),
    )
