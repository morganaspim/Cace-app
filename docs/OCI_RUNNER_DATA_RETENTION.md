# OCI runner data preservation and retirement

## Current boundary

The CACE OCI MCP server is intentionally not a general shell or file-transfer
interface. Do not add arbitrary shell execution or broad filesystem access to it
just to migrate data. The supported first step is a metadata-only inventory run
through the existing serialized collaboration workflow.

Known locations from the archived cache-prewarm and runner-diagnostics
workflows:

- `/var/lib/cace-cache/elan` — Lean toolchains installed by elan.
- `/var/lib/cace-cache/xdg` — XDG cache data.
- `/var/lib/cace-cache/mathlib` — pinned Mathlib package and compiled cache.
- `/var/tmp/cace-formal.*` — temporary formal build workspaces.

These are candidate locations, not a claim that all currently exist or contain
unique data. The inventory also does not establish that a runner is idle.

## 1. Inventory first (non-destructive)

On the PR branch, dispatch **CACE Collaboration Coordination Validation** and
set:

- `runner_data_inventory=true`

This mode is read-only. It records file names, sizes, modification times,
directory totals, and bounded largest/newest-file lists for the known cache and
temporary formal-build roots. It does not read file contents, follow symlinks,
read credential directories, create an archive, upload the cache, or delete
anything. The resulting `cace-oci-runner-data-inventory` artifact is a short
lived planning record, not a backup.

Review the inventory before choosing any export set. The walk is capped at
250,000 entries per root; a truncated result is not a complete inventory.

## 2. Choose the right durable destination

Do not commit machine caches, `.olean` files, or entire runner workspaces to
the Git repository. Keep Git for source, Lean toolchain declarations,
`lake-manifest.json`, proof plans, schemas, test fixtures, signed receipts,
and compact provenance manifests.

Recommended data classes:

| Data | Durable destination |
| --- | --- |
| Source, configs, manifests, proof plans, schemas, regression tests | Git, reviewed PR |
| Signed CACE receipts and small reproducibility manifests | Git or immutable evidence store, with digest and provenance |
| Runner logs and diagnostic bundles | OCI Object Storage, with lifecycle/retention policy |
| Large Lean/Mathlib cache and toolchain archives | OCI Object Storage, keyed by Lean version, Mathlib commit, OS/architecture, and cache format |
| Disposable build directories | Rebuild from pinned source after evidence capture; do not preserve by default |

Prefer a dedicated private OCI Object Storage bucket in the same tenancy and
region. Use instance principals from the exact CACE VM, a bucket-scoped IAM
policy, encryption at rest, object versioning or retention controls, and a
structured prefix such as:

```text
cace-runner-archive/<instance-id>/<UTC-date>/<inventory-id>/
  inventory.json
  manifests/
  diagnostics/
  cache/
```

Do not store secrets, OCI config, instance-principal tokens, GitHub runner
credentials, SSH material, environment files, or private keys in the archive.
Do not make the bucket public. GitHub Actions artifacts are suitable for the
small inventory and short-lived diagnostic evidence, not the multi-gigabyte
long-term cache.

## 3. Required export/verification/deletion protocol

A future exporter must implement this sequence as separate, auditable phases:

1. Select explicit allowlisted roots from the reviewed inventory.
2. Reject symlinks, special files, credential-like path components, and files
   outside the allowlist.
3. Produce a deterministic file manifest containing relative path, size, and
   SHA-256 for every selected regular file.
4. Stream the archive to OCI Object Storage without staging a second full-size
   archive on the runner filesystem.
5. Read the uploaded object back and independently verify object size and
   SHA-256 against the locally computed stream digest and manifest.
6. Write a completion receipt containing source instance identity, source
   paths, timestamps, object namespace/bucket/key/version, archive digest,
   manifest digest, tool version, and verification result.
7. Only after a separate operator approval, remove the exact exported files
   whose hashes match the verified manifest. Never use broad `rm -rf` patterns
   against cache roots. Never remove the active runner installation, active
   job workspace, or data modified since inventory/export.

An upload success response alone is not verification. A failed, partial, or
ambiguous export must leave the source data untouched. The exporter must be
idempotent and must refuse to overwrite an existing object version/key unless
explicitly requested.

## 4. Retirement order

Do not terminate the OCI VM or delete its boot volume as part of this data
migration. First export and verify the selected data, then prove that a clean
replacement runner can restore the required pinned Lean toolchain and Mathlib
cache and complete an exact-pin smoke build. Only then remove redundant cache
copies or retire the old runner. Keep the runner's source checkout recoverable
from Git and preserve the OCI instance/volume until the migration is signed off.

## 5. What this PR does not do

This PR adds only a read-only inventory mode and this runbook. It does not
upload, move, delete, or alter any OCI files, caches, instance settings, or IAM
policies. The inventory artifact is not a substitute for a backup. The actual
exporter and separately approved purge should be a follow-up change after the
inventory shows the real data volume and candidate files.
