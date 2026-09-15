# CACE Signed Attestations

CACE signed attestations are **provenance and independent-reproduction metadata**. They do not prove a theorem, do not change `VerificationRecord` state, and do not promote entries in the canonical claim registry or proof ledger.

## Cryptographic profile

- Signature algorithm: Ed25519.
- Implementation: the optional `cryptography` dependency.
- Statement serialization: existing `sha256/cace-canonical-json-v1` canonical JSON.
- Domain separator: `CACE:SIGNED-ATTESTATION:v1\0`.
- Verifier key identity: `ed25519:` followed by SHA-256 of the raw 32-byte Ed25519 public key.
- Envelope and statement both require `proof_effect: "none"`.

Every signed statement binds at least:

- verifier identity,
- verifier public-key identity,
- canonical CACE `claim_id`,
- exact evidence-bundle SHA-256,
- canonical UTC timestamp,
- purpose (`artifact-integrity` or `independent-reproduction`),
- optional additional bindings such as source commit or environment identity.

## Security boundary

A valid signature establishes that the holder of the corresponding private key signed the exact canonical statement. It does **not** establish that the scientific result is true, that the verifier is trustworthy, or that the underlying proof was kernel-checked.

Private keys are not repository artifacts and must never be committed. CACE must use vetted library primitives rather than custom signature or key-generation code.

## Future E5 cross-verification

A later policy layer may mark an artifact *eligible* for `E5 CROSS-VERIFIED` only when:

1. all lower mathematical/formal qualification gates already pass,
2. multiple distinct approved verifier keys sign the same `claim_id` and exact evidence-bundle hash,
3. every signature verifies,
4. verifier identities satisfy the configured independence policy.

That policy must remain separate from claim promotion and cannot turn provenance into mathematical truth.
