# Merlin RSI Production Readiness

Status: implemented validation bridge; production promotion remains fail-closed pending independently provisioned trust and a live CACE verifier transport.

## Evidence flow

1. Hermes emits a failure record bound to an event ID, source repository, exact 40-character commit, artifact SHA-256, failure class, and summary.
2. The Hermes receipt is verified against the server-pinned `hermes` issuer registry before the failure can become an RSI induction seed.
3. A worker dispatch is idempotent and accepts only a signed acknowledgement from the separately pinned `merlin-rsi-worker` issuer. The acknowledgement grants no promotion authority.
4. Candidate creation requires a signed `merlin-source` receipt. If derived from a Hermes failure, the candidate stores the exact induction seed event hash.
5. Evaluation stores the fixed benchmark manifest digest, normalized overall and per-domain metrics, all 25 normalized case results, the case-results digest, and a signed `merlin-evaluator` receipt. The evaluator signature binds the case-results digest and case count.
6. CACE evidence binds candidate ID and artifact digest, benchmark digest, evaluator receipt digest, source repository, and exact source commit. The CACE bundle digest is reproduced against the CACE EvidenceBundle v1 implementation.
7. A CACE attestation must be Ed25519-signed, have `proof_effect: none`, identify verifier `cace`, bind the exact bundle and candidate, and match the server-pinned CACE verifier key allowlist.
8. Promotion requires a separate signed `merlin-approver` receipt over the exact candidate, artifact, benchmark, and CACE attestation digests. A valid ledger chain is checked before promotion.

All candidate, evaluation, CACE-verification, and promotion events are stored in the append-only SQLite episode ledger. Update/delete triggers, canonical payload hashes, per-episode sequence numbers, and hash chaining are verified by the ledger checker.

## Server trust configuration

The pipeline reads trust from the execution environment, never from caller-provided arguments.

`MERLIN_ISSUER_TRUST_STORE_JSON` has this shape:

```json
{
  "schema": "merlin-issuer-trust-store-v1",
  "issuers": {
    "hermes": {"hermes-key-id": "-----BEGIN PUBLIC KEY-----..."},
    "merlin-source": {"source-key-id": "-----BEGIN PUBLIC KEY-----..."},
    "merlin-evaluator": {"evaluator-key-id": "-----BEGIN PUBLIC KEY-----..."},
    "merlin-rsi-worker": {"worker-key-id": "-----BEGIN PUBLIC KEY-----..."},
    "merlin-approver": {"approver-key-id": "-----BEGIN PUBLIC KEY-----..."}
  }
}
```

`MERLIN_ISSUER_TRUST_STORE_SHA256` must equal the SHA-256 digest of the exact UTF-8 JSON string supplied above.

`MERLIN_CACE_TRUST_STORE_JSON` has this shape:

```json
{
  "schema": "merlin-cace-trust-store-v1",
  "keys": [
    {"key_id": "ed25519:<64 lowercase hex characters>", "verifier_id": "cace", "status": "active"}
  ]
}
```

`MERLIN_CACE_TRUST_STORE_SHA256` must equal the SHA-256 digest of that exact UTF-8 JSON string. Inactive, duplicate, malformed, missing, or digest-mismatched trust entries are rejected.

These values must be provisioned by the runner/service administrator through a protected secret/configuration mechanism. They must not be committed to Git. The current OCI MCP capability report explicitly says secret access is not exposed. The read-only CACE MCP surface reports runtime health and control capabilities but does not expose an attestation issuance or verification operation. Therefore no live CACE endpoint or private signing key is assumed, and the production promotion gate stays closed until an independently administered CACE verifier/issuer integration and its pinned public key are available.

## Research metadata

Crossref DOI and arXiv identifier lookups use a persistent SQLite cache with response SHA-256 integrity checks, a 30-day default TTL, per-host persisted request clocks, minimum host intervals, bounded retries, Retry-After handling, and response-size limits. Metadata is discovery/provenance input only; it does not validate the cited research claim.

## Held-out evaluation and optional adapters

The frozen suite `merlin-rsi-multidomain-heldout-v1` contains 25 stable cases across mathematics, Lean, research, coding, and engineering. Suite changes require a new version. Candidate generators must not consume reference outputs; adapter comparisons must use paired cases.

The current OCI job validates the pipeline contracts and case-level ledger schema against this frozen manifest. The validator rejects missing/duplicate cases, domain mismatches, invalid scores, and unbound evaluator evidence. It does **not** claim that every task prompt has been run through a fully provisioned model/evaluator stack. Full task scoring still requires the separate domain evaluators and held-out execution harness.

GEPA and Inspect remain optional and disabled. The current gate requires at least 20 paired cases, a positive lower 95% confidence bound above the configured minimum gain, complete paired data in all five domains, and no per-domain regression. Eligibility is measurement-only; it does not automatically enable or promote an adapter. No adapter is enabled without actual paired held-out measurements.

## Latest OCI validation

- Repository: `morganaspim/Cace-app`
- Runner: `cace-oci-a1`, Linux ARM64
- Workflow run: `43123886846`
- Source commit: `bace7d4e553aa4637e971285a89839a2d14fdbc1`
- Result: Python compilation passed; 15/15 RSI pipeline tests passed.
- Benchmark manifest: frozen, 25 cases, five domains.
- No package installation or host mutation.

This is software regression evidence, not a production qualification receipt and not a mathematical proof. The promotion path remains fail-closed until independent CACE trust and transport are configured and the actual held-out evaluation workload is run.
