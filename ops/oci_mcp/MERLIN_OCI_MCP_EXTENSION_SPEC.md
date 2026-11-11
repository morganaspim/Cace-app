# Merlin OCI MCP Extension Specification

Status: design specification; not deployed or connected to a live OCI VM.

## Purpose

Extend the existing CACE OCI MCP into a shared, auditable access gateway for Merlin agents. Prefer the existing implementation in `ops/oci_mcp/`; do not create a second competing service or expose a generic shell.

The gateway should support safe inspection and controlled transfer of selected project artifacts while preserving the existing OCI runner, its caches, jobs, configuration, and data.

## Existing implementation (verified from repository source)

- `server.py` runs an MCP Streamable HTTP server at `127.0.0.1:8765/mcp` by default.
- OCI API authentication uses `InstancePrincipalsSecurityTokenSigner`.
- Current read tools cover capabilities, CACE runtime status, bounded CACE journal logs, instance/VNIC summary, and attached NSG rules.
- Current opt-in writes include CACE service restart and narrowly constrained NSG ingress changes.
- The server intentionally does not expose generic shell, secret access, IAM mutation, or arbitrary OCI API calls.
- The service is not a general SSH server and does not inventory the VM filesystem.

These are repository facts, not proof that the service is installed, reachable, healthy, or authorized on the current VM.

## Non-negotiable preservation policy

1. Never delete, truncate, overwrite, rename, move, chmod, chown, or replace an existing OCI file as part of inventory or transfer.
2. Never run cleanup, prune, cache eviction, package installation, deployment, service restart, provisioning, cutover, or disk-prewarm operations without a separately approved change plan.
3. Do not write archives, duplicate runner trees, temporary copies, indexes, or manifests to the OCI VM. Store inventory manifests and collected artifacts in GitHub or another explicitly approved external destination.
4. Never read or export private keys, tokens, credential files, environment files, cloud-init secrets, SSH agent sockets, or secret-manager values.
5. Do not read bulk model/cache contents. Inventory metadata first; retrieve only individually selected, bounded, non-secret files.
6. Do not run concurrent inventory jobs. One OCI operation at a time.
7. Stop if disk/inode headroom, instance identity, active job state, or authorization cannot be established.
8. A hash is an integrity identifier, not proof that an artifact is safe, correct, or independently verified.

## Proposed capability tiers

### Tier 0 — identity and headroom (read-only)

Add tools only after implementation and tests:

- `oci_get_instance_identity`: instance OCID, region, shape, lifecycle state, hostname, architecture, OS release; redact private IPs unless needed.
- `oci_get_storage_headroom`: filesystem mount, total/used/available bytes, percent used, inode totals/availability. Use bounded fixed commands or a small dedicated helper; never accept arbitrary command strings.
- `oci_get_active_runner_jobs`: bounded process/service metadata and runner job state without dumping environment variables or command-line secrets.
- `oci_get_runner_service_status`: allowlisted service names only; no restart action.

The first inventory action must establish identity, disk and inode headroom, and active work. If any check fails or is ambiguous, stop.

### Tier 1 — metadata-only inventory (read-only)

- `oci_list_allowed_roots`: return only explicitly configured roots.
- `oci_inventory_tree`: return relative path, type, size, mtime, mode, and optional content digest; bounded depth, entry count, elapsed time, and byte budget.
- Deny symlinks by default; never follow paths outside an approved root.
- Exclude credential paths and sensitive file patterns by policy. Do not return file contents.
- Return a continuation cursor for bounded pagination; never silently truncate and imply completeness.
- Record exclusions, errors, caps, and inventory timestamp.

Suggested initial roots (must be verified against the actual VM before enabling): `/opt/actions-runner`, `/home/morganaspi/actions-runner`, and the CACE MCP deployment root. These are historical candidates, not confirmed current paths.

### Tier 2 — selected file retrieval (read-only)

- `oci_read_approved_file`: only files under approved roots, explicit relative path, maximum file size, UTF-8/text allowlist, no symlink traversal.
- Deny private keys, certificates with private material, tokens, environment files, credential stores, shell history, process environments, and secret-bearing config.
- Require an explicit path; no recursive content harvesting.
- Return content plus SHA-256, byte count, source path, instance identity, retrieval time, and truncation status.
- Do not read a file if it exceeds the configured cap; return a refusal and metadata instead.

### Tier 3 — outbound artifact transfer (controlled)

Prefer transfer from the VM to a GitHub branch or approved external artifact store using a dedicated identity with the minimum required permission. No GitHub write token should be placed on the VM if an external broker can perform the write.

- Only selected, non-secret files may be transferred.
- Create new destination paths; never replace existing files by default.
- If the destination exists, stop and request a new path or explicit review.
- Record source path, source instance, byte count, SHA-256, destination commit/artifact identifier, and transfer result.
- No bulk runner directory or cache upload.

### Tier 4 — bounded execution (future, disabled by default)

Do not expose a generic `exec(command)` tool. If future build jobs are required, use an allowlisted job registry with typed parameters, isolated workspaces, explicit resource budgets, deadlines, cancellation, output caps, and durable job receipts. Jobs must not mutate the existing runner installation or caches. Use a separate workspace or external runner where possible.

## MCP transport and ChatGPT connectivity

- Keep the current service bound to loopback.
- Do not expose port 8765 directly to the public Internet.
- Use a supported authenticated remote MCP transport or secure tunnel with TLS, OAuth or equivalent strong client authentication, authorization scopes, rate limits, and audit logging.
- A local stdio server or a Markdown skill file alone does not connect this hosted ChatGPT session to the VM.
- Never embed a private SSH key, OCI API key, token, or secret in this repository, skill file, MCP arguments, logs, or chat.
- Prefer OCI instance principals for OCI API calls from the VM. For SSH-based access, use a dedicated, rotated, least-privilege identity and a supported secure transport; the key pasted into chat must be treated as compromised and rotated.

## Required tool response envelope

Every operation should return a structured receipt:

- `status`: success | partial | refused | error
- `operation_id`: unique stable identifier
- `instance_id` and `region`
- `started_at`, `finished_at`
- `policy_version`
- `limits_applied`
- `items_returned`, `bytes_returned`
- `warnings`, `excluded_paths`, `errors`
- `content_digest` when content is returned

Never claim full inventory if pagination, exclusions, permissions, or limits prevented full coverage.

## Implementation and acceptance sequence

1. Review current installer and service lifecycle before any deployment. The current `install.sh` contains a release-directory removal operation; do not run it against the existing VM. Replace that deployment behavior in a separately reviewed change before any installation attempt.
2. Add pure policy helpers and unit tests for path containment, symlink rejection, sensitive-path exclusion, entry/byte/depth caps, pagination, and destination no-overwrite behavior.
3. Add Tier 0 tools first. Test locally with fakes; label those results as simulated, not live OCI evidence.
4. Add Tier 1 metadata inventory; test boundary cases and resource limits.
5. Add Tier 2 selected-file retrieval with strict deny rules.
6. Add Tier 3 outbound transfer only after Tier 0–2 are qualified.
7. Establish authenticated remote MCP connectivity and verify it from an authorized client.
8. Run a live read-only smoke test: identity, headroom, active jobs, then metadata-only inventory.
9. Keep all writes, installs, restarts, cutovers, and merges separately approval-gated.

## Evidence and verification

For each release, preserve:
- source repository and commit SHA;
- artifact digest;
- tool and policy version;
- test results and fixtures;
- deployment/change approval;
- live instance identity;
- operation receipts and bounded logs;
- independent CACE verification where qualification is claimed.

A documentation PR or passing unit test does not prove live OCI connectivity or live runner inventory.
