# Titan ML-DSA v2 Attestation

Status: schema added; signer/verifier implementation pending independent API review and official-vector verification.

The new `cace-signed-attestation-v2` schema is additive. It does not alter or reinterpret the existing Ed25519 v1 envelope. V2 fixes the signature algorithm to ML-DSA-65 (FIPS 204), binds the canonicalization profile and a versioned domain separator, requires a public-key-derived key identifier, and carries exact repository, source commit, workflow run, provider commit and ACVP vector source commit bindings.

The accompanying `scripts/verify_titan_bundle.py` independently recomputes the CACE evidence bundle identity and Merkle root and verifies every supplied artifact's bytes against its declared digest and size. It deliberately does not claim signature validity, mathematical proof correctness, FIPS 140 validation or cryptographic qualification.

## Remaining gates

- Implement ML-DSA signing and verification using a vetted provider API, not custom cryptography.
- Test key encoding and public-key-derived IDs across two independent providers.
- Run official FIPS 204 ACVP vectors on the exact provider build.
- Add positive, tamper, malformed-canonicalization and key-mismatch tests.
- Add trust policy, key rotation and revocation handling.
- Run this verifier against the actual Avrea evidence bundle and retain the complete verifier run.
