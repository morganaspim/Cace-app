# Merlin OCI Access Bridge — Safe Implementation Contract

**Status:** design and implementation contract; not evidence of live OCI connectivity.  
**Date:** 2026-11-11  
**Scope:** give Merlin and other authorized AI clients a repeatable, auditable way to request bounded work from the existing OCI runner without exposing SSH credentials or turning the VM into an unrestricted shell.

## 1. Current verified boundary

The GitHub repository is `morganaspim/Cace-app`. The active work includes draft PR #82 (OCI qualification workflow) and draft PR #83 (integrated Merlin engineering skill). The documented OCI host is an Oracle Linux 8 ARM64 VM, historically described as VM.Standard.A1.Flex with 2 OCPU and 12 GB RAM. The repository also documents `/opt/actions-runner`, CACE/Lean/Mathlib/telemetry caches, and `/opt/cace-oci-mcp`.

These are **repository/documentation observations**, not a fresh inventory of the live VM. The most recent runner evidence available to this work showed push-triggered qualification runs queued with no runner assigned. No SSH session, live filesystem inspection, runner command, or OCI-side change is claimed here.

## 2. Security decision: do not give an AI a raw SSH key

A private key pasted into a chat or stored in a handoff Markdown file is not a safe credential-distribution mechanism. Never put private keys, passphrases, OCI API keys, GitHub tokens, or other secrets in:
- this repository, issues, pull requests, artifacts, logs, prompts, or handoff documents;
- MCP tool descriptions or tool arguments;
- command-line arguments, environment dumps, or diagnostic output.

If a private key was exposed in a conversation, treat it as compromised and rotate/revoke it through the credential owner before further use. Do not copy the exposed key into a new location.

A Markdown file can transfer **instructions, resource maps, API contracts, and safety policy** between AI systems. It cannot itself grant network reachability, create an SSH client, provision an MCP server, or transfer credentials.

## 3. Preferred connection pattern

Use the already-existing CACE OCI MCP service if it is present, healthy, authenticated, and its actual source and deployed configuration can be inspected. The documented path `/opt/cace-oci-mcp` is only a lead; its existence and contents must be checked by an authorized operator or a successfully assigned existing runner before relying on it.

If that service does not expose the required operations, implement a narrow **Merlin OCI Gateway MCP** alongside it (do not replace it). The gateway is a policy-enforcing adapter, not an SSH-key vending machine:

```
Merlin / authorized AI client
        |
        | authenticated MCP request; typed operation
        v
Merlin OCI Gateway (allowlist + budgets + audit)
        |
        | local runner/job adapter; no AI-visible SSH key
        v
Existing OCI self-hosted runner / CACE execution environment
        |
        +--> read-only inventory and bounded file reads
        +--> approved test/build jobs in isolated workspaces
        +--> job status, logs, checksums, receipts
```

The gateway should run under a dedicated unprivileged service identity. The SSH or runner credential, if one is required internally, remains host-held and is never returned to the model. Prefer local execution through the already-installed runner over opening a new inbound SSH port. Do not change firewall, SSH daemon, runner labels, service units, or network policy as part of initial implementation.

## 4. Minimum MCP surface

Expose explicit typed tools; do not expose `ssh(command)`, arbitrary shell, unrestricted file write, or unrestricted sudo.

| Tool | Initial authority | Required behavior |
|---|---|---|
| `oci.status` | read-only | Runner online/idle/busy, service health, timestamp, identity |
| `oci.inventory` | read-only | OS/architecture, CPU/RAM, mount-level disk totals/free, runner version/labels, cache names/sizes; redact secrets |
| `oci.list_paths` | read-only | List only configured roots; reject traversal and symlinks escaping roots |
| `oci.read_file` | read-only | Allowlisted text files, byte/line limits, redact secret-like values |
| `oci.submit_job` | constrained | Submit a named, versioned job profile; no caller-supplied shell command |
| `oci.job_status` | read-only | Durable state, queue age, worker identity, exit status |
| `oci.job_logs` | read-only | Bounded, redacted log slices with content digest |
| `oci.artifact_manifest` | read-only | Artifact names, sizes, SHA-256, source commit, job ID |
| `oci.cancel_job` | constrained | Cancel only a job created by this gateway; never kill arbitrary processes |

Initial named job profiles should be limited to:
1. `inventory_snapshot` — read-only host and cache inventory.
2. `merlin_python_smoke` — pinned, bounded, non-destructive Python test subset in an isolated worktree.
3. `cace_lean_canary` — the repository's existing pinned Lean canary, only after the runner is confirmed online and the exact commit/toolchain are recorded.

Do not enable arbitrary package installation, cache pruning, service restarts, runner re-registration, system updates, broad filesystem writes, deployment, or proof promotion through the gateway.

## 5. Request and receipt contracts

Every request must carry:
- `request_id`: caller-generated UUID, idempotent across retries;
- `actor_id`: authenticated client identity;
- `operation`: exact allowlisted operation/profile;
- `repository`, `commit_sha`, and `workspace_id` where applicable;
- `requested_limits`: timeout, CPU, memory, disk, output bytes;
- `reason`: concise task purpose.

Every completed job must return a durable receipt containing:
- request ID and gateway job ID;
- authenticated actor and selected profile/version;
- repository and exact checked-out commit SHA;
- runner identity, OS, architecture, and tool versions;
- start/end timestamps, timeout and resource limits;
- exit code and terminal state (`succeeded`, `failed`, `timed_out`, `cancelled`, `rejected`);
- stdout/stderr artifact paths and SHA-256 digests;
- artifact manifest and SHA-256 digests;
- explicit `qualification=false` unless the separate canonical CACE qualification process independently attests otherwise.

A job receipt proves what the runner reports it did; it is not by itself a proof of mathematical correctness, CACE verification, or canonical qualification. CACE must independently verify any evidence-bearing artifact against its exact source, toolchain, and provenance.

## 6. Non-destructive operating invariants

These are hard requirements, not suggestions:

- Preserve all existing OCI and GitHub contents. No deletion, overwrite, cleanup, cache eviction, disk reclamation, reformatting, re-provisioning, restart, or replacement.
- Do not modify existing runner configuration or labels.
- Use a new isolated workspace for each job. Do not build in or mutate the runner's existing checkout or cache directories.
- Read-only inventory precedes any job submission.
- Enforce disk headroom before staging; reject rather than reclaim space.
- Use per-job CPU, memory, disk, process-count, network, output-size, and wall-clock budgets.
- Default network egress to denied; explicitly allow only required repository/artifact endpoints if policy permits.
- Use immutable job inputs and idempotency keys; ambiguous submissions must be reconciled by request ID, never blindly replayed.
- Keep logs redacted and bounded. Never log credentials or secret values.
- A failed or disconnected gateway must fail closed; no fallback to arbitrary SSH or shell execution.
- Do not merge PRs or deploy from the gateway. Source changes go through isolated branches and reviewable PRs.

## 7. Authentication and authorization

Use the host's existing secret manager or OS-protected credential store. Do not create a new user-managed setup step if an existing authenticated runner identity can satisfy the need. Each MCP client receives a distinct identity and narrowly scoped authorization.

Suggested roles:
- `observer`: status, inventory, allowlisted reads, job status/logs/manifests.
- `builder`: observer rights plus submission of approved named job profiles in isolated workspaces.
- `operator`: separately authenticated human authority for sensitive host operations; not available to AI clients in the initial release.

Authentication must be checked on every request. Authorization must bind actor, operation, repository, branch/commit, workspace, and budget. Revocation must invalidate active sessions and queued-but-not-started jobs. No tool may infer authority from a claimed actor name in request JSON.

## 8. Implementation sequence and acceptance gates

### Gate A — establish facts (read-only)
1. Inspect the repository source for `/opt/cace-oci-mcp` implementation, deployment notes, service identity, authentication, tool schemas, and tests.
2. Inspect current runner workflow and labels from repository configuration.
3. Obtain a fresh runner assignment and inventory receipt through an existing authorized path.
4. Record the difference between repository claims, runner-reported state, and independently verified state.

**Pass:** exact source revision and service configuration are known; runner identity is observed; no host mutation occurred.

### Gate B — gateway contract and local tests
1. Define versioned JSON schemas for the tools and receipts.
2. Implement strict decoding, unknown-field rejection, path allowlists, redaction, per-actor authorization, budgets, request idempotency, and append-only audit.
3. Add tests for traversal, symlink escape, secret leakage, malformed inputs, cross-actor access, expired/revoked identity, duplicate submissions, timeout, cancellation, output truncation, and audit failure.
4. Keep the gateway disabled for execution until all tests pass.

**Pass:** tests prove that rejected requests cause no host-side effect and all accepted actions produce an auditable receipt.

### Gate C — read-only live pilot
1. Deploy only through the existing approved mechanism, without replacing CACE MCP or changing runner configuration.
2. Run status and inventory only.
3. Compare reported OS/architecture/resources/paths with a second independent observation.
4. Confirm secrets are absent from outputs and logs.

**Pass:** two matching, timestamped read-only observations; no filesystem mutation.

### Gate D — bounded job pilot
1. Enable only `inventory_snapshot`, then `merlin_python_smoke`.
2. Use a fresh isolated workspace and pinned commit.
3. Record resource usage and artifact digests.
4. Have CACE independently inspect the receipt and exact artifacts.
5. Enable `cace_lean_canary` only after its own prerequisites are met.

**Pass:** successful bounded execution, reproducible source/tool identity, integrity-checked artifacts, and no impact to existing checkouts/caches.

### Gate E — production readiness
Require threat model, dependency review, authentication/revocation tests, concurrency tests, resource-pressure tests, audit retention policy, incident procedure, and explicit operator sign-off. Keep the gateway's initial authority read-only plus the three named profiles.

## 9. Immediate next actions

1. Continue using GitHub's repository/PR interface for source changes; keep the existing OCI qualification PR #82 draft until actual runner evidence exists.
2. Inspect the existing CACE OCI MCP source and tests before designing a duplicate service.
3. Determine why the existing push-triggered OCI job remains queued (runner offline, labels mismatch, repository runner access, or capacity) using GitHub-visible evidence; do not alter labels speculatively.
4. Once an existing runner is assigned, run only a read-only inventory first.
5. Implement the narrowest missing gateway operation on a separate branch and submit a draft PR.

## 10. Cross-agent handoff

Any AI continuing this work must:
- read this contract and the integrated Merlin engineering skill;
- inspect current PRs, branches, and exact commit heads before writing;
- never assume the live OCI host is reachable because its address or path is documented;
- never request, print, store, or reuse a private key pasted into a chat;
- preserve all existing OCI/GitHub contents and work only in new isolated branches/workspaces;
- distinguish proposed, repository-observed, runner-reported, and independently verified facts;
- make changes as additive PRs; do not merge or deploy;
- report exact commits, files, tests, runner IDs, and receipts, and explicitly state what did not run.

**Current conclusion:** the most useful free route is the existing GitHub self-hosted runner plus its existing CACE OCI MCP integration, provided that runner can be brought online through already-authorized infrastructure. A free MCP wrapper alone cannot create SSH reachability or safely conjure credentials. Build the gateway as a narrow, auditable bridge only after inspecting and reusing the existing service.
