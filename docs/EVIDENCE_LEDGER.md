# CACE Evidence Ledger v1

CACE Evidence Ledger is a tamper-evident **provenance and reproducibility** layer. It does not prove mathematics, upgrade scientific evidence, or authorize claim promotion.

## What it establishes

An evidence bundle can bind exact artifact bytes to contextual metadata such as a claim ID, Git commit, proof-source hash, dependency/toolchain identity, experiment identity, or verification certificate. Each artifact is addressed by SHA-256. Artifact manifests are canonicalized with the existing `sha256/cace-canonical-json-v1` reproducibility contract and committed into a domain-separated Merkle tree.

Ledger entries then commit bundles into an append-only SHA-256 hash chain. Mutation, deletion, replacement, or re-linking is detectable when the chain is verified from genesis.

This supports questions such as:

- Are these the same proof, source, dependency, experiment, and result artifacts that were previously attested?
- Did any artifact bytes change?
- Did a historical ledger entry change or disappear?
- Do independent verifiers refer to exactly the same evidence bundle?

It does **not** answer:

- Is a theorem mathematically true?
- Did Lean's kernel accept a proof?
- Are assumptions sufficient?
- Is a numerical experiment a continuum theorem?
- Should a claim become formally verified or cross-verified?

Those decisions remain with CACE's verification, claim-registry, proof-ledger, formal-kernel, axiom-audit, and claim-promotion gates.

## Canonical identity

`cace_studio.core.reproducibility` is the one canonical JSON layer. Evidence Ledger reuses:

`sha256/cace-canonical-json-v1`

No second canonicalization format is introduced.

The Evidence Ledger adds domain separation for its own structures:

- artifact leaf: `CACE:EVIDENCE:ARTIFACT-LEAF:v1`
- Merkle node: `CACE:EVIDENCE:MERKLE-NODE:v1`
- bundle: `CACE:EVIDENCE:BUNDLE:v1`
- ledger entry: `CACE:EVIDENCE:LEDGER-ENTRY:v1`

Artifact order supplied by callers has no semantic effect. Artifacts are sorted deterministically by `(artifact_id, sha256)` before Merkle construction. Artifact IDs must be unique. For odd Merkle levels, the final digest is duplicated before computing the parent.

## Fail-closed semantics

Every bundle and ledger entry contains:

```json
"proof_effect": "none"
```

Any attempt to construct a bundle or ledger entry with another proof effect fails validation. Unknown schema names or hash algorithms also fail closed.

A bundle may contain labels such as `claim_id`, `runtime_state`, or `requested_evidence` in its bindings. Those are provenance metadata only. They cannot promote a claim. The authoritative promotion logic remains outside this module.

## Evidence bundle

A bundle contains:

- schema and algorithm identifiers,
- one or more artifact manifests,
- a Merkle root,
- contextual bindings,
- notes,
- `proof_effect: "none"`.

An artifact manifest contains a stable artifact ID, SHA-256 of exact bytes, byte length, role, media type, optional path, and optional metadata.

When artifact bytes are available, verification requires an exact ID set and verifies both byte length and digest. A partial subset is rejected.

## Append-only ledger

A ledger entry contains a zero-based sequence, caller-supplied UTC timestamp string, evidence-bundle SHA-256, bundle Merkle root, previous-entry SHA-256 (or `null` at genesis), metadata, entry SHA-256, and `proof_effect: "none"`.

Verification walks from genesis and checks sequence, previous-hash linkage, and every entry hash. If bundle objects are supplied, their bundle digests and Merkle roots are checked too.

The timestamp is provenance supplied by the caller. In v1 it is **not** a trusted timestamp authority.

## Security boundary

v1 intentionally does not implement digital signatures, key storage, consensus, a cryptocurrency, or a custom blockchain.

Hash integrity is not identity. Anyone can hash a bundle. A future attestation layer should use a reviewed signature implementation such as Ed25519 through a vetted cryptographic library, with explicit key identity and rotation rules. A later adapter may anchor signed roots into an external transparency service or public ledger, but such anchoring remains optional.

Even with signatures or a blockchain, provenance is not truth. Compromised verifier hosts, stolen signing keys, malicious dependencies, incorrect formal assumptions, and non-reproducible builds remain separate threats.

## Cross-verification direction

A future CACE cross-verification policy can require multiple independent verifier identities to attest the **same** bundle digest and Merkle root, while also requiring all lower mathematical/formal gates to pass. The evidence ledger can establish sameness and history; it cannot replace those gates.

## Schemas and implementation

- `schema/evidence-bundle-v1.schema.json`
- `schema/evidence-ledger-v1.schema.json`
- `cace_studio/core/evidence_ledger.py`
- `tests/test_evidence_ledger_v331.py`
