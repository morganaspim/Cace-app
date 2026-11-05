# Titan ML-DSA v2 Attestation

**Status:** implementation present; actual Avrea evidence bundle independently verified by CACE; final ML-DSA receipt test is blocked by CACE OCI runner disk exhaustion.

## Profile

The additive `cace-signed-attestation-v2` schema uses ML-DSA-65 (FIPS 204). It preserves the existing Ed25519 v1 envelope unchanged. V2 binds:

- canonical statement serialization and versioned domain separator;
- verifier identity and public-key-derived key ID;
- exact CACE bundle digest and claim ID;
- source repository and full source commit;
- workflow run ID;
- exact liboqs provider commit and NIST ACVP vector source commit;
- explicit verification scope, purpose and `proof_effect: "none"`.

The implementation is in `cace_studio/core/pqc_attestation.py`. It uses the pinned liboqs provider, checks the key ID against the supplied public key, verifies public/secret keypair consistency before emitting a signature, and supports an explicit trusted key-ID check during verification.

## CLI

The existing CACE attestation CLI now exposes:

- `pqc-keygen`: generates ML-DSA-65 verifier keys; private key file is created with restrictive permissions.
- `pqc-sign`: signs a canonical CACE evidence bundle. It requires `--artifact-root` and recomputes every artifact byte digest before signing.
- `pqc-verify`: verifies the envelope and can pin both `--trusted-verifier-id` and `--trusted-key-id`.

Private signing keys must remain outside Git and CI artifacts. The test workflow uses ephemeral keys only; no production signer key has been provisioned or used.

## Evidence and verification

- Provider baseline: liboqs 0.16.0 at commit `5a1a854b0dc9f2141bdc771c555ee60c37950183`.
- Python binding: liboqs-python 0.16.0.2 at commit `64c76ad0a80d6c69f2003219eb27b253782a3d68`. Upstream documents this patch as fixing short-key ML-DSA signature forgery and ML-KEM shared-secret recovery behavior; earlier binding versions are excluded.
- NIST ACVP source: ACVP-Server tag `v1.1.0.41`, commit `b121fee031dc65d32c96f4109a42a10dacbe2076`. The tag commit is pinned, but its GitHub commit is unsigned.
- Avrea run `42090360334`: 54 selected standardized ACVP tests passed, with zero failures: FIPS 203 ML-KEM 9/9, FIPS 204 ML-DSA 9/9, FIPS 205 SLH-DSA 36/36.
- CACE OCI run `42091465065`: the `cace-oci-a1` runner independently reconstituted the exact Avrea workflow archive and verified its original archive digest and four extracted evidence artifacts.
- The actual Avrea archive is also included in the ML-DSA receipt test fixture. The CACE ML-DSA workflow's native provider and Python binding installation succeeded on cace-oci-a1 in run 42092942992. The retained job log shows the CLI test failed before its final verification assertion because the test passed a Path object to public_key_id instead of the key bytes. The latest branch test now passes public_key.read_bytes(). A later run 42093924533 has no step records, no retrievable logs and no artifact; its run result is failure, but it provides no test result. The branch handoff reports disk exhaustion on cace-oci-a1 as the operational blocker; do not infer a successful ML-DSA receipt test until the latest exact-head run completes and retains its logs.

## Remaining qualification gates

- Reclaim disk on `cace-oci-a1`, then rerun the ML-DSA receipt roundtrip and CLI test workflow.
- Review the profile independently and test against a second vetted ML-DSA implementation.
- Define production trust policy, key rotation, revocation and signer custody.
- Keep NIST ACVP vector testing distinct from FIPS 140 module validation.
- Require CACE verification, mathematical qualification, and separate production approval before promotion.

A valid signature authenticates the canonical statement and key possession. It does not prove a theorem, prove the cryptographic construction secure, or confer production authority.
