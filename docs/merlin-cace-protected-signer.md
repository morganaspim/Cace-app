# Merlin CACE protected signer boundary

## Status

This document specifies the deployment boundary for CACE RSI reproduction signing. The current OCI job gateway is a branch-triggered, fixed-profile test runner. It is **not** a signing service, and it must never receive the CACE private signing key.

The Python verifier exposes an in-memory PEM parameter so a separately deployed trusted service can load key material from its secret manager without writing a key file. This interface alone does not configure a signer, establish trust, or authorize production signing.

## Trust boundary

1. Treat all `merlin/oci-jobs/**` commits, request JSON, source artifacts, and test output as untrusted input.
2. Keep the signing service code on a protected, reviewed revision. Do not import the service implementation from a request branch or execute it in the branch-triggered OCI workflow.
3. Load the private key from a protected secret manager into process memory only. Never log it, echo it, put it in an Actions artifact, or write it to a workspace/cache.
4. Pin the expected SHA-256 of the exact approved `.github/workflows/merlin-oci-job-gateway.yml` bytes in trusted signer configuration, independently of the request branch. The signer must pass that pin as `trusted_workflow_sha256`; missing or malformed pins fail closed.
5. Verify the exact successful run, expected fixed operation, source repository/commit, complete source blob manifest, frozen benchmark manifest, runner identity, successful required steps, and retained artifact digest before signing.
6. Pin the resulting CACE public key in Merlin's trust store through a separately reviewed change. Rotation/revocation must be explicit and auditable.
7. Return only the signed attestation and public provenance. Authority remains `verification-only`, with `proof_effect=none`. Promotion requires a separate signed approval.

## Required signer configuration

- Protected service revision and deployment identity
- Secret-manager reference for the Ed25519 private key
- Independently pinned workflow-file SHA-256
- CACE core runtime revision and dependency lock
- GitHub API read credential scoped to the single CACE repository and Actions run/artifact reads
- Allowlisted source repository and fixed RSI benchmark contract
- Public-key trust-store digest and rotation policy

No value should be accepted from the request payload to override these settings.

## Current blockers

- The OCI MCP currently has no attestation/reproduction tool and reports secret access disabled.
- No protected signer endpoint or secret-manager binding has been confirmed.
- No trusted workflow-file digest has been provisioned.
- No live CACE reproduction attestation has been issued.

Until all blockers are resolved, this integration is code-only and must not be represented as production CACE verification.
