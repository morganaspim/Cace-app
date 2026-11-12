# CACE OCI MCP Control Plane

This directory contains a deliberately narrow Model Context Protocol (MCP) server
for operating the CACE Oracle Cloud Infrastructure VM.

The server is **not** a generic shell and **not** a generic OCI API proxy. It is
designed to expose a small audited set of actions to an MCP client.

## Exposed tools

Read-only by default:

- `get_control_capabilities`
- `get_cace_runtime_status`
- `get_cace_logs`
- `get_oci_instance_summary`
- `get_attached_nsg_rules`
- `verify_merlin_rsi_attestation` (read-only; CACE-native bundle/signature verification)
- `get_github_runner_status`

Opt-in write tools:

- `restart_cace_web`
- `ensure_web_ingress`
- `remove_mcp_managed_web_ingress`

The network write tools:

- only operate on an NSG already attached to this instance,
- only add TCP 80/443 ingress,
- require a canonical source CIDR,
- mark rules with `CACE-MCP-MANAGED`,
- only remove rules carrying that marker,
- never mutate subnet security lists.

The service exposes no arbitrary command execution, IAM mutation, secret access,
instance termination, or generic OCI SDK method. The Merlin RSI verifier delegates
bundle and Ed25519 semantics to `cace_studio.core`, and it cannot sign attestations
or promote claims.

The `get_github_runner_status` tool is a bounded, read-only host snapshot. It
reports Actions runner directory/registration-file presence, listener process,
matching systemd units, filesystem capacity, OS/architecture/CPU and aggregate
memory, plus the local `cace-oci-mcp` service and whether TCP 8765 is bound to
loopback or a non-loopback address. It never reads runner credentials, contacts
GitHub, or exposes arbitrary shell. GitHub assignment/online state is reported
as unobserved by the host probe and must be established from a matching Actions
job. CI retains the snapshot as a run artifact for audit.


## Repository checkout manifest

The collaboration-validation artifact also includes `collaboration-validation-summary.json`. Its v10 manifest hashes every Git-tracked file present in the exact PR checkout, records missing tracked files, lists tracked paths changed or staged inside the runner workspace, and records safe untracked source/document candidates by path, size, and SHA-256. Sensitive-looking paths, environment files, caches, virtual environments, and non-source file types are excluded from the untracked candidate list; their count is reported separately.

The untracked scan uses Git's `--exclude-standard`, so ignored paths (including ignored caches and virtual environments) are not enumerated. This is evidence about the checked-out repository workspace for that workflow run. It does **not** enumerate the entire OCI filesystem, ignored files, files outside `GITHUB_WORKSPACE`, copy untracked files into GitHub, or prove that arbitrary pre-existing runner files were committed to the PR. Review the candidate manifest and explicitly add any required source files through a separate reviewed commit. No workspace cleanup or file deletion is performed by this inventory step.

## Authentication model

Run the server on the OCI VM and authenticate to OCI with an **instance
principal**. Do not put OCI API keys in the MCP server.

The Python SDK uses:

```python
oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
```

The MCP HTTP endpoint listens on loopback only:

```text
http://127.0.0.1:8765/mcp
```

Use a supported secure tunnel / remote MCP publishing mechanism rather than
opening port 8765 to the Internet.

## 1. Get the exact VM identity

On the OCI VM:

```bash
curl -fsS \
  -H 'Authorization: Bearer Oracle' \
  http://169.254.169.254/opc/v2/instance/
```

Record:

- `id` — the instance OCID
- `compartmentId` — the compartment OCID
- `region`

IMDSv2 is used intentionally.

## 2. Create the dynamic group

Create a dynamic group named, for example:

```text
CACE_OCI_MCP
```

Use an **exact-instance** matching rule:

```text
instance.id = '<CACE_INSTANCE_OCID>'
```

Do not match every instance in the tenancy or compartment unless that broader
scope is intentionally required.

## 3. Add read-only IAM policy first

Replace `<CACE_COMPARTMENT>` with the actual compartment name or use the
compartment OCID form supported by OCI policy syntax.

```text
Allow dynamic-group CACE_OCI_MCP to read instances in compartment <CACE_COMPARTMENT>
Allow dynamic-group CACE_OCI_MCP to read vnics in compartment <CACE_COMPARTMENT>
Allow dynamic-group CACE_OCI_MCP to use network-security-groups in compartment <CACE_COMPARTMENT>
```

This supports the read tools. It does not grant generic tenancy administration.

## 4. Optional: permit only NSG rule updates

Only add this policy when ChatGPT/MCP should be allowed to add or remove the
MCP-managed web ingress rules:

```text
Allow dynamic-group CACE_OCI_MCP to manage network-security-groups in compartment <CACE_COMPARTMENT>
  where request.permission='NETWORK_SECURITY_GROUP_UPDATE_SECURITY_RULES'
```

The separate `use network-security-groups` line above is retained for listing
rules. The server code independently restricts writes to attached NSGs and
ports 80/443.

Do **not** grant `manage virtual-network-family` or `manage all-resources`
for this MCP service.

## 5. Install on the VM

From a checkout of this repository:

```bash
bash ops/oci_mcp/install.sh
```

The installer:

- creates the dedicated `cace-mcp` system account,
- installs an isolated Python virtual environment,
- installs the MCP + OCI SDK dependencies,
- installs the systemd service,
- installs a sudoers rule that permits only
  `systemctl restart cace-web`,
- starts the service on `127.0.0.1:8765`.

Check it:

```bash
sudo systemctl status cace-oci-mcp --no-pager
ss -ltn | grep 8765
```

## 6. Enable write capabilities separately

The default environment is fail-closed:

```text
CACE_OCI_MCP_ALLOW_SERVICE_RESTART=false
CACE_OCI_MCP_ALLOW_NETWORK_WRITE=false
```

After the relevant IAM/local privilege configuration has been reviewed:

```bash
sudoedit /etc/cace-oci-mcp.env
```

For example:

```text
CACE_OCI_MCP_ALLOW_SERVICE_RESTART=true
CACE_OCI_MCP_ALLOW_NETWORK_WRITE=true
```

Then:

```bash
sudo systemctl restart cace-oci-mcp
```

Enable only the capability you actually want.

## 7. Connect an MCP client

The server uses MCP Streamable HTTP at:

```text
http://127.0.0.1:8765/mcp
```

For ChatGPT, use a remote MCP connection or Secure MCP Tunnel rather than
publishing this loopback endpoint directly. If you choose to expose it through
a public reverse proxy instead, add strong authentication (prefer OAuth),
TLS, rate limits, and a hostname allowlist; do not publish an unauthenticated
MCP endpoint.

## Merlin RSI attestation verification

The read-only `verify_merlin_rsi_attestation` MCP tool is an independent CACE
verification endpoint for Merlin RSI evidence. It:

- parses and verifies the supplied CACE EvidenceBundle and exact artifact bytes using CACE core (10 MiB aggregate request limit);
- verifies the signed attestation using CACE core Ed25519 verification;
- requires purpose `independent-reproduction`, exact claim and bundle digests,
  and exact expected bindings;
- checks the signer key ID against a server-loaded, digest-pinned trust store;
- returns only a verification result with `proof_effect=none` and
  `authority=verification-only`.

The caller cannot provide trusted keys. Configure the public-key pin document
in `/etc/cace-oci-mcp.env` using `CACE_MERLIN_RSI_TRUST_STORE_JSON` and
`CACE_MERLIN_RSI_TRUST_STORE_SHA256`. The JSON schema is
`merlin-cace-trust-store-v1` and contains active Ed25519 key IDs bound to
verifier identity `cace`. The SHA-256 must be computed over the exact UTF-8
JSON string. The public key itself is carried in the attestation and its
fingerprint must match the pinned key ID.

Set `CACE_APP_ROOT` only if the CACE Studio release is not available at
`/opt/cace-web/current`. The tool fails closed if CACE core, cryptography, or
the trust store is unavailable. It does not generate signatures, run arbitrary
candidate code, establish mathematical truth, or grant promotion authority.
Promotion remains a separate Merlin approval decision.

## Operational boundary

CACE application deployment remains a GitHub-controlled workflow. This MCP
surface intentionally focuses on OCI/runtime/network operations so the VM does
not need a long-lived GitHub write token.

Formal CACE qualification is a separate evidence system. Restarting a service
or changing an NSG never creates or upgrades proof evidence.
