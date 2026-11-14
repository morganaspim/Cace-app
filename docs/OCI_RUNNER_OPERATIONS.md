# OCI Self-Hosted Runner Operations and Setup

**Scope:** operations guide for the existing CACE OCI Actions runner and loopback OCI MCP control plane. This is not authorization to provision, resize, re-register, clean, or mutate the host.

## Current operational target

- GitHub repository: `morganaspim/Cace-app`
- Known runner name: `cace-oci-a1`
- Required Actions labels: `self-hosted`, `cace`, `oci`, `aarch64`
- Architecture: Linux ARM64 / AArch64
- Runner root observed by the inventory implementation: `/opt/actions-runner`
- OCI MCP endpoint: `http://127.0.0.1:8765/mcp` (loopback only)
- MCP service: `cace-oci-mcp.service`
- Persistent cache roots used by exact-pin workflows: `/var/lib/cace-cache/elan`, `/var/lib/cace-cache/mathlib`, `/var/lib/cace-cache/lake` and related cache directories.
- Latest observed successful collaboration validation: run #655, commit `a9b8a9c661c7271e40d8927c1622c67ced52ccdb`; runner inventory and read-only MCP probe both passed. This proves those probes succeeded for that run, not that every host subsystem is healthy now.

**Important:** the exact current instance shape, free disk, RAM, service state, GitHub online state and cache integrity must be read from a fresh inventory/job. Never treat this document's prior snapshots as live telemetry.

## Safety rules

1. Do not terminate, recreate, resize, re-register, or replace the current OCI VM as a routine fix.
2. Do not delete caches, workspaces, evidence, logs, or unknown files to free space. Cache pruning must use the existing reviewed reserve-aware policy and must never touch pinned dependency truth.
3. Do not use the archived provisioning workflow as a current installer. Its historical user-data includes an `ocarun` NOPASSWD-all sudoers grant. That is overbroad and must not be copied or revived.
4. Never pass a registration token, OCI credential, private key, or secret in a workflow input, command-line log, issue, PR, or repository file.
5. Never expose TCP 8765 to the public Internet. Keep MCP bound to `127.0.0.1`; use an approved authenticated tunnel/publishing mechanism if remote access is needed.
6. Do not add OCI tenancy-wide IAM. Use an exact-instance dynamic group and least-privilege policies.
7. Write capabilities remain disabled by default. Read-only inventory/probe success does not authorize service restart, network changes, signing, or deployment.
8. Runner provisioning/registration requires an explicit owner-approved change window and a reviewed rollback plan.

## Existing GitHub Actions runner setup (reference only)

The existing host's runner is expected under `/opt/actions-runner`. A fresh install or registration is **not** part of normal CI. If a replacement is explicitly approved, use the following controlled sequence:

1. Provision an OCI Linux ARM64 instance only after confirming the approved shape, region, compartment, subnet, storage, backup, budget and rollback. Do not use an archived workflow's hardcoded shape or automatic termination behavior as current authority.
2. Create a dedicated unprivileged account (historical setup used `github-runner`) and a dedicated runner directory. Install only required OS dependencies from trusted distribution repositories.
3. Download a currently supported official GitHub Actions runner release for Linux ARM64. Pin the release version and verify the published checksum/signature before extraction. Do not silently float to latest.
4. Create cache directories owned by the runner account, with explicit quotas/reserve policy. Do not put runner credentials in shared caches.
5. In GitHub repository Settings → Actions → Runners, create a short-lived registration token. Treat it as a secret; use it once, interactively, and discard it. Do not write it to shell history or CI logs.
6. Register only to `https://github.com/morganaspim/Cace-app`, with name `cace-oci-a1` (or an explicitly approved replacement name) and labels `cace,oci,aarch64`. Do not register the runner at organization or account scope unless separately approved.
7. Install the runner as a systemd service under the unprivileged runner account. Enable restart-on-failure with bounded backoff. Verify `.service` metadata exists without reading or printing `.credentials` or other credential files.
8. Add only the environment paths required for pinned Lean/Mathlib caches. Keep the runner service's writable paths narrow. Do not grant passwordless unrestricted sudo to the runner user.
9. Verify with read-only inventory and a trivial non-mutating Actions job. Confirm the exact runner labels, service state, OS/architecture, free disk, memory and GitHub assignment from the job itself.
10. Retain setup receipts, image/instance identity, runner release checksum, service definition, IAM policy revision and inventory digest in a protected evidence store. Never include registration tokens or credential contents.

Do not automate runner registration by embedding a token in cloud-init or an Actions workflow. Use an owner-controlled interactive step.

## OCI MCP service setup

The repository-owned implementation is under `ops/oci_mcp/`:
- `install.sh` — installs the dedicated `cace-mcp` service account, isolated Python venv, requirements, systemd unit and sudoers allowlist.
- `cace-oci-mcp.service` — binds to loopback, uses a dedicated account, read-only hardened systemd settings and only the service's state directory as writable.
- `server.py`, `policy.py`, `runner_inventory.py`, `health_probe.py` — fixed typed operations and bounded read-only inventory/probe.
- `requirements.txt` — MCP SDK, OCI SDK and cryptography version ranges; production deployments should capture the resolved package lock/manifest as evidence.

### Preconditions

- Verify the exact instance OCID and region from OCI IMDSv2 on the host.
- Use an OCI instance principal, not a user API key file.
- Create an exact-instance dynamic group. Do not match every VM in the compartment.
- Start with read-only IAM for instance, VNIC and attached NSG inspection. Add narrowly scoped NSG update permission only if the user separately approves network writes.
- Keep the MCP HTTP endpoint on loopback. Use an authenticated tunnel; do not open inbound 8765.

### Install and verify

From a reviewed repository checkout on the OCI host:

```bash
bash ops/oci_mcp/install.sh
sudo systemctl status cace-oci-mcp --no-pager
ss -ltn | grep 8765
```

Expected listener: `127.0.0.1:8765`. The installer is a privileged operation; review its exact commit and diff before running it. It should not be run from an untrusted PR checkout.

Fail-closed environment defaults in `/etc/cace-oci-mcp.env`:
```ini
CACE_OCI_MCP_ALLOW_SERVICE_RESTART=false
CACE_OCI_MCP_ALLOW_NETWORK_WRITE=false
CACE_OCI_MCP_ALLOW_MERLIN_RSI_SIGNING=false
```

Do not enable any write flag as part of runner setup. Signing requires separate external signer/trust design and explicit approval.

## Routine read-only health checks

Use the fixed repository workflows/tools, not arbitrary shell:
- Collaboration validation captures `oci-runner-inventory.json` and `mcp-readonly-probe.json`.
- The inventory reports bounded host metadata, runner directory/registration marker presence, listener process, matching service units, filesystem capacity, architecture/CPU/memory and MCP loopback listener state.
- Host inventory deliberately reports GitHub online state as unobserved; the corresponding Actions job proves only that the runner accepted that job.
- The Merlin OCI gateway exposes only fixed request profiles; do not send shell commands or caller-selected tool names.

Before any expensive Lean or package job, check current disk headroom and pinned cache presence. Historical gateway documentation recorded approximately 0.5 GiB free on a 30 GiB root filesystem; this is a stale warning, not a live measurement. If reserve is insufficient, stop and request an approved capacity plan. Do not improvise deletion.

## Recovery and change control

If the runner is offline:
1. Confirm the latest GitHub runner assignment state through a workflow/job, not host inventory alone.
2. Collect read-only instance/service/inventory evidence.
3. Check systemd status and journal through the approved operator path.
4. Determine whether the issue is VM state, runner service, network, registration expiry, or GitHub scheduling.
5. Propose a bounded change and rollback before any restart/re-registration.
6. After approved recovery, run inventory, MCP read-only probe, and a no-op Actions job; retain receipts.

Never print or upload runner `.credentials`, `.credentials_rsaparams`, registration tokens, OCI private keys, environment-file secret values, or process command lines that may contain secrets.


## Merlin ArtifactRef independent trust-root inputs (2026-11-14)

The ArtifactRef verifier no longer accepts a trust-store JSON payload and digest supplied together by the caller. Its verifier now requires:
- `CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PUBLIC_KEY_PEM`: public Ed25519 trust-root PEM, provisioned through the protected deployment configuration path;
- `CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_AUTHORITY_ID`: stable trust authority identifier;
- `CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_VERSION`: positive root configuration version;
- `CACE_MERLIN_ARTIFACT_REF_TRUST_ROOT_PROVISIONING_IDENTITY`: separately administered provisioning identity;
- `CACE_MERLIN_ARTIFACT_REF_TRUST_STORE_SECRET_OCID`: OCI Vault secret OCID containing the root-signed trust-store receipt.

The OCI instance principal reads the trust-store secret. The secret payload is a canonical signed receipt containing the v2 trust-store payload, its SHA-256, root key ID, and Ed25519 signature. The verifier checks expiry and key status and returns trust-root and trust-store version/digest metadata.

**Required OCI IAM separation:** the CACE instance principal receives only `read secret-bundles` for the designated trust-store secret. It must not receive secret create/update/delete or vault/key administration permissions. Trust-store updates belong to a separate trust administration identity. The protected deployment pipeline controls the root public-key pin and its provisioning identity. Review actual compartment scope, dynamic-group membership, policies, secret OCID, and deployment environment protections before enabling the feature.

The configuration labels are not themselves an IAM proof. Production qualification requires inspecting OCI policy and protected deployment settings, then running a protected end-to-end test. Do not paste private keys, bearer tokens, secret payloads, or OCIDs into chat or logs. Until configured and independently inspected, report the capability as unavailable/unqualified.
