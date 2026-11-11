# Merlin OCI Job Gateway

**Status:** initial read-only job gateway; not a remote shell or general-purpose MCP endpoint.

## Purpose

Provide Merlin and authorized AI clients with a safe way to submit a bounded job to the existing OCI Actions runner using the connected GitHub repository as the control plane. The gateway avoids SSH credentials, inbound firewall changes, public exposure of the OCI MCP port, and any new paid service.

The enabled profiles are deliberately narrow: `inventory_snapshot` and `mcp_readonly_probe`. The second profile performs a local Streamable HTTP initialize/tools-list handshake and calls only fixed read-only MCP tools. Neither profile installs packages, builds software, modifies caches, or changes host configuration.

## Request protocol

A request is a single JSON file at:

```
merlin/oci-requests/<request-uuid>.json
```

It must be committed on a branch matching:

```
merlin/oci-jobs/<unique-request-branch>
```

The push event must add or modify exactly one request file and must not delete files.

Example:

```json
{
  "schema": "merlin-oci-job-request-v1",
  "request_id": "6f0b4d3a-2c71-4e89-9a65-1b3f8d7c0e42",
  "operation": "inventory_snapshot",
  "reason": "Verify OCI runner and local MCP service state",
  "created_at": "2026-11-11T20:15:00Z"
}
```

The workflow rejects unknown or missing fields, a mismatched filename/request ID, malformed timestamps, oversized reasons, removed files, multiple changed files, unsupported operations, and branches outside the dedicated namespace.

## Enabled profiles

| Profile | State | Authority |
|---|---|---|
| `inventory_snapshot` | Enabled | Read-only runner and local MCP inventory |
| `merlin_python_smoke` | Disabled | Requires a separate disk-headroom gate and isolated test environment |
| `cace_lean_canary` | Disabled | Requires at least 8 GiB free disk and pinned toolchain/cache verification |

The workflow does not accept commands, shell strings, package names, arbitrary paths, or caller-selected scripts. The MCP probe is hardcoded to `http://127.0.0.1:8765/mcp` and permits only `get_control_capabilities`, `get_cace_runtime_status`, and `get_github_runner_status`. Unknown operations and tool names fail closed.

## Execution and trust boundaries

- GitHub Actions is the authenticated control plane; the workflow uses its short-lived `GITHUB_TOKEN` with `contents:read` only to fetch the request and pinned inventory source.
- The workflow does not run `actions/checkout`, so it does not clean or overwrite the existing runner workspace.
- The executable inventory module is fetched at the exact request commit and its Git blob SHA must match the reviewed source pin in the workflow.
- The inventory profile executes the reviewed read-only `collect_runner_status` function.\n- The MCP probe sends only protocol initialization, tool discovery, and the three fixed read-only calls listed above; it never accepts a tool name from the request.
- The job has a three-minute wall-clock limit; each host probe has a five-second timeout.
- No package installation, cache mutation, service restart, network policy change, deployment, cleanup, or host write is permitted.
- The request's claimed actor is not trusted; the receipt records the GitHub push event's authenticated sender.
- A workflow run is not proof qualification. Receipts explicitly set `qualification=false` and `proof_implication=none`.

## Receipt and artifact

Each successful request returns a GitHub Actions artifact containing:

- `job-receipt.json`: request ID and digest, authenticated actor, repository and exact commit, runner identity, workflow run/attempt, start/end times, source module blob SHA and SHA-256, status, fixed resource limits, and qualification boundary.
- `runner-inventory.json`: bounded host inventory, including OS/architecture/CPU/RAM/disk, Actions runner process/service, CACE OCI MCP service, and loopback listener status.

Artifacts are stored under a unique run/attempt directory in `RUNNER_TEMP` and uploaded with a unique artifact name. Existing paths are never reused or cleaned.

## Operating procedure

1. Create a unique request branch from the reviewed gateway branch.
2. Add one request JSON file whose filename matches `request_id`.
3. Push the branch; the push triggers the gateway workflow.
4. Retrieve the workflow run and its artifact through GitHub.
5. Verify the receipt's commit, request digest, module blob SHA, runner ID, and status before using the inventory.
6. Do not infer mathematical proof, CACE qualification, or general job execution authority from an inventory receipt.

## Current constraints

The OCI VM currently has approximately 0.5 GiB free on its 30 GiB root filesystem. The gateway's inventory profile is designed to run within that constraint. Python and Lean test profiles remain disabled until disk headroom is restored through an explicitly approved preservation-safe capacity plan. No existing files or caches are to be deleted to make room.
