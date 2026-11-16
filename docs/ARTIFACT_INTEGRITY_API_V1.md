# CACE Artifact-Integrity API v1

## Status

Implemented on branch `feat/cace-artifact-integrity-api-v1`. This is source code only. It is not deployed, has not been configured with credentials or a signing key, and has not been qualified by CI or an independent production run.

## Scope

`POST /api/verification/artifact-integrity` accepts only `source_file_snapshot` bundles. For every artifact, CACE:

1. Validates the request schema and exact bundle bindings.
2. Resolves the exact 40-character source commit through the authenticated GitHub commit API.
3. Fetches each declared repository-relative file at that exact commit.
4. Independently compares the fetched bytes with the artifact size and SHA-256 in the bundle.
5. Compares the fetched bytes with the submitted artifact bytes.
6. Recomputes the canonical bundle digest and Merkle root.
7. Signs an Ed25519 attestation with purpose `artifact-integrity` and self-verifies it.

Generated build outputs, rendered media, numerical results, and other non-source artifacts are deliberately rejected. They require a future protocol that verifies trusted builder provenance; a commit label alone is not sufficient.

The response always sets `proof_effect=none`, `qualification=false`, and `semantic_correctness=not_established`. This endpoint does not qualify a Lean proof, certify a scientific claim, or promote a capability.

## Runtime configuration

The endpoint fails closed with HTTP 503 unless all of the following are supplied by the deployment's secret manager:

- `CACE_ARTIFACT_INTEGRITY_TOKEN`: dedicated bearer credential for Merlin callers.
- `CACE_GITHUB_API_TOKEN`: GitHub token with read access to the source repositories being checked.
- `CACE_ARTIFACT_INTEGRITY_PRIVATE_KEY_B64`: base64-encoded Ed25519 PKCS#8 PEM private key.
- `CACE_ARTIFACT_INTEGRITY_TRUSTED_KEY_ID`: pinned `ed25519:<sha256>` key ID. Startup/request-time validation rejects a signer whose derived key ID differs.
- `CACE_ARTIFACT_INTEGRITY_VERIFIER_ID`: stable CACE verifier identity.

No credentials, keys, or trust-root values belong in source control. No production secret or trust-root has been created or changed by this implementation.

## Request contract

The exact request keys are:

- `schema`: `cace-artifact-integrity-request-v1`
- `source_repository`: GitHub `owner/repository`
- `source_commit`: full lowercase 40-character Git commit SHA
- `artifact_kind`: `source_file_snapshot`
- `tool_version`: non-empty version string
- `bundle`: canonical CACE evidence-bundle payload; its bindings must repeat the exact repository, commit, artifact kind, and tool version
- `artifact_bytes_base64`: exact map from every bundle artifact ID to its base64 bytes

Every bundle artifact must have a unique normalized repository-relative `path`. Path traversal, missing/extra artifact bytes, mismatched source content, unknown request fields, and unsupported artifact kinds are rejected.

## Resource limits

- 8 MiB per source file.
- 24 MiB total decoded artifact bytes.
- GitHub API requests use an 8-second timeout.
- No arbitrary URLs are accepted; all source retrieval targets the fixed GitHub API host.

A future hardening pass should add an HTTP request-body cap before JSON parsing and a strict maximum artifact count before production exposure.

## Merlin integration contract

Merlin must pin the expected verifier key ID independently, send the exact source-file snapshot bundle and bytes, verify the returned Ed25519 envelope against that pinned key, and check every statement binding before accepting the receipt. The receipt remains provenance-only and must never be passed to the Lean proof-verification adapter as if it were an independent-reproduction proof.
