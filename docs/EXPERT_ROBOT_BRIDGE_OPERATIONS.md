# Expert Robot bridge and runner operations (CACE side)

This page documents the CACE half of the Merlin / Expert Robot execution bridge for any AI coding agent with authorized access to this repository.

**Read first:** `AGENTS.md`, `CACE_AGENT_BOOTSTRAP.json`, `docs/BUILD_AND_TRUST_GUIDE.md`, `docs/SECURITY_ARCHITECTURE.md`, then this page. The Expert Robot-side operational guide is in `Mannyspiro/expert-robot/docs/AI_RUNNER_AND_BRIDGE_OPERATIONS.md`. Always fetch the live source and run evidence; handoff documents are not current-state proof.

## 1. Repository roles

- CACE repository: `morganaspim/Cace-app`.
- Persistent source and policy branch: `main`.
- Canonical workflow/base branch: `executor/expert-robot-bridge`.
- Per-attempt request branches: `cace-request/<request-id>`.
- Per-request result branches: `cace-result/<request-id>`. 
- Upstream dispatcher/source repository: `Mannyspiro/expert-robot`.
- Upstream source branch currently used by the integration: `feat/hermes-routing-eval-avrea-discovery-20261105`.
- Canonical generator for the CACE bridge workflow: `Mannyspiro/expert-robot/.github/workflows/external-free-runner-bridge.yml`, inside the literal `BRIDGE_YAML` heredoc. A new request regenerates the bridge branch from the CACE default branch. Do not make durable policy or documentation edits only on the generated branch.

## 2. Runner inventory

### CACE qualification runner

- Workflow: `.github/workflows/expert-robot-bridge.yml` on `executor/expert-robot-bridge`.
- Job: `qualify`.
- Labels: `[self-hosted, cace, oci, aarch64]`.
- Runner is a self-hosted OCI ARM64 worker. The actual machine name is recorded in `bridge/result.json` as `machine`; architecture is recorded as `architecture`.
- Permissions: `contents: read`; checkout sets `persist-credentials: false`.
- Qualification lane: `formal-static-arm64`, requested lane `cace-oci-aarch64`.
- Lean pin: `leanprover/lean4:v4.34.0`.
- Mathlib pin: `5ed2965256430c3649e86755f9576b54eca72435`.
- The workflow requires at least 2 GiB free disk before installing the exact Lean toolchain. Check the exact mount/cache path and available disk before retrying. Do not remove unrelated data or caches.

The OCI worker is not the result publisher and is not given the Expert Robot reverse deploy key. It validates the request and archive, runs bounded checks, writes structured evidence, and uploads the result artifact.

### CACE publisher runner

- Job: `publish-result`, on `ubuntu-latest`.
- Runs with `if: always()` after the qualification job, so a qualification failure can still be returned as structured evidence.
- Has `contents: write` and `actions: read` scoped to CACE-app.
- Downloads the qualification artifact, validates the envelope, publishes `bridge/result.json` and `bridge/result.log` on the bridge branch, and attempts the optional reverse SSH return.
- A CACE repository write is not a write permission to Expert Robot.

## 3. Request and qualification lifecycle

1. Expert Robot's Avrea hosted Actions dispatcher packages a bounded source archive and creates a unique `cace-request/<request-id>` branch from `executor/expert-robot-bridge`. It pushes `bridge/request.json` and the source archive only; the canonical CACE workflow is inherited from the base branch.
2. Request schema v2 binds request ID, full Expert Robot commit SHA, source branch, return repository, requested lane and qualification-only authority.
3. The CACE workflow validates request/source identity and archive members. It rejects absolute paths, traversal, symbolic/hard links, devices and FIFOs.
4. It scans the Lean source for selected proof escapes and checks the exact Lean/Mathlib revisions.
5. It executes the bounded static/formal qualification checks and records log output and runner identity.
6. It emits result schema v3 with `pass` or `fail`, integer exit code, request ID, Expert Robot commit, CACE repository/commit/workflow ID/ref/run/attempt, runner labels/machine/architecture, Lean/Mathlib pins, log SHA-256/size, and `authority=qualification-only`, `promotion_authority=false`.
7. The publisher validates the result and publishes it to `cace-result/<request-id>`. It then attempts the optional reverse deploy-key path.

A failed qualification is a valid result. Preserve the failure envelope and log. The publisher should fail only for a malformed or mismatched envelope, missing artifact, or publication/transport failure—not simply because the qualification status is `fail`.

## 4. Credential boundaries

### Forward transport key

The forward CACE-app deploy key is stored on the Expert Robot side. Expert Robot prefers `CACE_BRIDGE_SSH_PRIVATE_KEY` and falls back to the established legacy alias `RAILWAY_SSH_PRIVATE_KEY`. CACE agents do not need to read or recreate it.

The legacy secret name does not mean this is a Railway API credential. It is an SSH transport credential for the CACE-app repository. It is not a CACE verifier token or signing key.

### Optional reverse transport key

The CACE Actions workflow recognizes these secret names, in order:

1. `EXPERT_ROBOT_SSH_PRIVATE_KEY`
2. `EXPERT_ROBOT_DEPLOY_KEY`
3. `CACE_TO_EXPERT_ROBOT_SSH_KEY`
4. `EXPERT_ROBOT_DEPLOY_PRIVATE_KEY`

The reverse key must be a separate deploy key scoped to `Mannyspiro/expert-robot`. It is not the forward CACE-app key. If configured, the publisher creates `cace-return/<request-id>` with the request, result and log; it never merges.

The recorded run found none of these reverse secrets configured. Therefore reverse SSH is not confirmed working. Do not create non-empty placeholders, display secret values, ask the user to paste private keys, or commit credentials. An authorized maintainer must configure a real deploy key in GitHub Actions secrets and test it.

### Verifier signer identity

SSH deploy keys establish repository transport access only. They do not authenticate a CACE qualification result. Current result envelopes are unsigned unless a CACE Ed25519 signing key is independently provisioned and the Expert Robot consumer verifies the signature against a trusted public key. Never describe unsigned result JSON as cryptographically authenticated.

## 5. Evidence and trust interpretation

Keep these states distinct:

- **Transport succeeded:** request reached CACE or result bytes returned.
- **Envelope valid:** producer and consumer agree on schema and bound identity fields.
- **Integrity checked:** log/result hashes match the actual bytes.
- **Qualification pass/fail:** exact checks ran and returned their exit status.
- **Signer authenticated:** trusted Ed25519 signature verified against an approved signer identity/key ID.
- **Independent verification:** verifier has checked the exact artifact/commit/toolchain under the trust policy.
- **Promotion:** separate human/policy-controlled action; never implied by any preceding state.

A valid schema and hash are not signer authentication. A Lean compile is not independent CACE verification. A CACE runner result does not grant theorem promotion or additional authority.

## 6. CACE workflow inspection runbook

For each request, capture:

- `bridge/request.json` and its SHA-256;
- exact Expert Robot full source commit;
- CACE bridge workflow file and its CACE commit;
- workflow ID, run ID and attempt;
- qualify and publish-result job IDs and every step conclusion;
- `bridge/result.json`, `bridge/result.log`, and artifact ID/digest;
- runner machine, architecture, Lean version, Mathlib commit;
- result status, exit code and authority fields.

Use repository **Actions** → **Expert Robot Free Runner Bridge** → exact run → **Jobs** and **Artifacts**. Check both jobs: `qualify` can fail due to qualification while `publish-result` can still validate and publish the failure envelope.

For disk issues, inspect the runner log lines for `Disk before Lean install`, `df -h`, and `insufficient disk space`. Do not infer that a cached toolchain is present merely because a cache directory exists; validate the executable and exact version.

For envelope failures, compare the producer's schema/version/field types with the consumer in the generated workflow. Validate request ID, Expert Robot commit, CACE repo/commit/workflow/run/attempt, status/exit consistency, log digest and log size. Preserve a valid FAIL.

## 7. AI agent operating rules

- Fetch the current CACE branch and exact workflow file before making a change.
- Read the root `AGENTS.md` instructions and the linked trust documents.
- Do not use `executor/expert-robot-bridge` as a persistent documentation branch.
- Treat `executor/expert-robot-bridge` as the immutable workflow/base branch; use unique `cace-request/<request-id>` branches for incoming requests and `cace-result/<request-id>` for returned evidence. Do not rebase or delete evidence on a shared request branch.
- Do not run unbounded commands on the self-hosted runner or bypass the workflow.
- Do not change Lean/Mathlib pins or delete caches just to get a green run.
- Do not claim a test ran unless the Actions job step is completed and its logs show execution.
- Do not claim reverse SSH works until its key-preparation and return steps succeed.
- Do not claim signer authentication until the Ed25519 signature verifies against a trusted key.
- Do not merge, deploy, promote claims, or expand authority without explicit approval.

The durable operational guide in Expert Robot is the canonical cross-repository runbook. This page records the CACE-specific boundary and trust rules; it must remain consistent with the live generated workflow.
