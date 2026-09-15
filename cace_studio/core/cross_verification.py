from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from .attestation import SignedAttestation, verify_attestation
from .claim_registry import ClaimRegistry
from .proof_ledger import ProofLedger

E5_STATUS = "E5-CROSS-VERIFIED"
PROOF_EFFECT = "none"


@dataclass(frozen=True)
class CrossVerificationResult:
    claim_id: str
    bundle_sha256: str
    qualified_commit: str | None
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
    minimum_independent_verifiers: int = 2,
) -> CrossVerificationResult:
    """Evaluate CACE E5 eligibility without mutating proof qualification.

    E5 is an additional cross-verification label over an already-qualified
    canonical claim. It never creates or promotes a mathematical proof.
    """
    if minimum_independent_verifiers < 2:
        raise ValueError("E5 requires at least two independent verifiers")
    registry = registry or ClaimRegistry.load_default()
    ledger = ledger or ProofLedger.load_default()
    claim = registry.by_id(claim_id)

    reasons: list[str] = []
    qualified_commit: str | None = None

    if claim is None:
        reasons.append("claim_id is not present in the canonical claim registry")
    else:
        qualified_commit = claim.attested_commit
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

        if claim is None or not claim.attested_commit or not claim.proof_artifact_sha256:
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
        eligible=eligible,
        status=E5_STATUS if eligible else "E5-NOT-ELIGIBLE",
        verifier_ids=tuple(sorted(valid_verifiers)),
        verifier_key_ids=tuple(sorted(distinct_keys)),
        reasons=tuple(reasons),
    )
