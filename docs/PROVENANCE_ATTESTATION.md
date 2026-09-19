# Immutable Scientific Provenance and Distributed Attestation

Status: approved later-phase architecture. Not yet a production feature and not part of the trusted mathematical proof mechanism.

## Purpose

CACE should make a scientific result tamper-evident and independently reproducible by binding the exact claim, source, dependencies, inputs, certificates and outputs to cryptographic identities. This is provenance infrastructure. It does not turn an incorrect theorem or incorrect computation into a correct one.

## Core principle

Mathematical truth continues to come from the appropriate verifier: Lean/kernel checking for formal theorems, exact or symbolic checkers for exact claims, interval methods for certified bounds, and explicit numerical tests for numerical claims. Cryptographic provenance answers a different question: "Is this exactly the artifact that was checked, and who attested to checking it?"

## Proposed bundle

A deterministic CACE research bundle should be able to address at least:

- canonical claim ID and scoped statement;
- source repository and exact commit;
- theorem/proof source digests;
- Lean/toolchain and dependency lock identities where applicable;
- `.cace` experiment identity;
- canonical input and parameter digests;
- dataset/content digests;
- output/result digests;
- run certificate and verification-record digests;
- proof/certificate-checker version identities;
- platform/build metadata where relevant to reproduction;
- explicit nonclaims, unresolved obligations and evidence level.

The bundle should use canonical serialization so the same logical artifact has the same content identity. Large artifacts may be referenced by content address rather than embedded.

## Merkle composition

Individual artifact digests should be assembled into a deterministic Merkle tree. The Merkle root becomes the compact identity of the complete research bundle. Inclusion proofs can then demonstrate that a particular theorem, dataset, result or certificate belongs to the attested bundle without requiring every consumer to transfer the whole bundle.

The Merkle root does not assert correctness. It identifies content.

## Signed attestations

A verifier attestation should bind its signature to at least:

- the claim ID;
- Merkle root / artifact digest;
- exact source commit;
- verifier software/toolchain identity;
- verification procedure and result;
- timestamp or monotonic ledger position;
- verifier key identity;
- explicit scope and nonclaims.

Private signing keys must never be stored in the repository. Key rotation and revocation must be supported. A signature from an unknown or untrusted key proves possession of that key, not scientific authority.

## Transparency ledger

CACE may maintain an append-only transparency log of attestation records. Entries should be hash-linked or Merkle-accumulated so deletion/reordering/equivocation becomes detectable. The ledger should be independently mirrorable and verifiable from exported records.

The transparency ledger must not be required to run CACE locally or verify a self-contained mathematical certificate.

## Optional external immutable anchoring

Periodically, a transparency-ledger checkpoint or Merkle root may be anchored to an established public timestamp or blockchain system. This can strengthen evidence that a particular checkpoint existed no later than a public time and make retrospective tampering harder.

CACE should not create a cryptocurrency or custom consensus network for this purpose. No token is necessary. Network anchoring is optional and must not control scientific evidence status.

## Distributed reproduction

Independent machines or organizations may reproduce a bundle and issue separate signatures over the same content identity. A future `E5 CROSS-VERIFIED` policy can require a threshold or policy-defined set of successful artifact-bound attestations.

CACE can mechanically verify that signatures are distinct and bind to the same artifact. CACE cannot infer genuine institutional independence merely from different keys. Identity, conflicts of interest and reviewer independence remain external trust questions unless backed by a separately defined identity/trust framework.

## Relationship to the existing proof ledger

The v3.31 claim registry/proof ledger is the immediate foundation. It already requires exact commit binding, content-addressed proof artifacts, workflow provenance and fail-closed promotion. The later provenance layer should generalize this into deterministic research bundles, signatures, Merkle inclusion proofs and an append-only transparency history without weakening existing promotion rules.

## Operational run-log preservation

Provider-hosted CI logs are not durable scientific provenance by themselves. Critical verification and qualification runs should produce a self-contained run bundle before depending on GitHub, Vercel, or another orchestration UI to retain logs.

Recommended storage hierarchy:

- durable local runner directory;
- persistent host journal;
- versioned OCI Object Storage mirror;
- optional independent secondary mirror;
- provider-native logs/artifacts as an additional copy.

The run manifest should hash stdout/stderr, step exit codes, exact source commit, relevant environment/toolchain identities, and produced evidence artifacts. The resulting manifest digest may be enrolled into the CACE transparency/evidence ledger.

This strengthens auditability and disaster recovery only. Log retention and hashing do not make a theorem or computation correct.

## Failure behavior

Missing network connectivity, missing external anchor, unavailable remote verifier or an unverifiable signature must be reported explicitly. CACE must never convert those conditions into a mathematical failure if the underlying self-contained proof is valid, nor into a provenance PASS if the requested provenance check did not run.

## Security considerations

The design must address canonicalization ambiguity, hash agility, malicious artifact substitution, replay, key compromise, revocation, timestamp semantics, ledger equivocation, dependency confusion and privacy of unpublished research. SHA-256 may be the initial content hash, but serialized records should identify the hash algorithm so future migration is possible.

## Recommended implementation order

First stabilize canonical artifacts and the v3.31 proof ledger. Then add deterministic research-bundle manifests and Merkle roots, local signing/verification, append-only transparency records, independent reproducer attestations, key rotation/revocation and only then optional external timestamp/blockchain anchoring.
