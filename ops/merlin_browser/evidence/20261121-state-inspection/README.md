# Fixed browser state inspection

This separate diagnostic explains the existing-state guard failure from [run 44956695079](https://github.com/morganaspim/Cace-app/actions/runs/44956695079). That run passed 33 controller controls, 41 product tests and the corrected Base64 transport, then stopped before its operation intent. The error identified none of the six protected paths. No new browser submissions were reached, and no fresh remaining-budget observation was obtained.

The diagnostic can collect observations only. It neither imports nor calls the acceptance controller. The existing acceptance workflow, controller, six-path absence guard, runtime, helpers and budgets remain unchanged. Every receipt has `acceptance_allowed: false`, including when all six paths are absent. A completed inspection does not authorize cleanup or another acceptance run.

## Exact request contract

The new workflow is `.github/workflows/merlin-browser-state-inspection.yml`. It accepts a push to `merlin/browser-operations-20261121` that adds exactly one file:

```text
merlin/browser-state-inspection-requests/<new-canonical-uuid>.json
```

The request has exactly four fields:

```json
{
  "schema": "merlin-browser-state-inspection-request/1",
  "request_id": "<new-canonical-uuid>",
  "operation": "inspect-state-44956695079",
  "created_at": "<current-UTC-YYYY-MM-DDTHH:MM:SSZ>"
}
```

The placeholders above are documentation, not a request file. The canonical request UUID must differ from the failed requests and retained predecessor. The workflow accepts only its first attempt, the fixed repository/ref and `cace-oci-a1` runner under UID 1000 with Python 3.9. The privileged inspector separately requires native root/aarch64/Python 3.9 and a run ID after 44956695079. Request fields cannot select paths, units, commands, resources or actions.

Definitions publication must contain no request file. Before a distinct diagnostic request is published, the parent coordinator must verify the exact new definitions and current serialized lane state. This proposal makes no remote write or dispatch.

## Read boundaries

The inspector holds the existing operation lock and observes the six paths from the failed run. In particular, the staged UUID is the **failed request's UUID**, not the new diagnostic request's UUID:

| Fixed path | Permitted observation |
|---|---|
| `/var/lib/merlin-browser-bootstrap/3eadad53-ba62-4a35-9578-eebe65420f76` | Metadata only |
| `/var/lib/merlin-browser-bootstrap/ledger-successor-from-18106dfc-0a56-4b68-9d30-5d334d7d6a69.json` | Metadata; bounded exact JSON only if trusted |
| `/opt/merlin-public-browser/releases/ebdca90a42bbb243ac04872bdf3f1210ea20583cce9b4c34c7867af1873cb959` | Metadata only |
| `/opt/merlin-public-browser/current` | Metadata and literal link target |
| `/run/merlin-public-browser/browser.sock` | Metadata only; no connection |
| `/var/lib/merlin-public-browser/episodes/recovered-arxiv-18106dfc-0a56-4b68-9d30-5d334d7d6a69` | Metadata only |

Metadata includes type, UID/GID, mode, device and inode. Parent directory traversal and leaf observations refuse symlink following; a link target is read as text, capped at 1,024 bytes. No protected directory is recursively scanned or listed.

Marker content is limited to 32 KiB. Reading requires a root-owned, regular, single-link file without group/other write permission. The opened descriptor and final directory entry must match the original inode and metadata before exact JSON/hash is reported. Missing, untrusted, changed or unreadable content is explicit; errors never become absence or authority to continue.

The inspector's only subprocess is a bounded `systemctl show` of `merlin-public-browser.service`, requesting the fixed fields listed in the inspector, with a 5-second deadline and 16-KiB output cap. `/proc/net/unix` is read with a 128-KiB cap; the receipt exports at most 16 rows whose path exactly equals `/run/merlin-public-browser/browser.sock`. Unrelated and near-matching socket rows are not exported. No socket is contacted.

No corpus, provider or package inventory is read. There is no deletion, cleanup, service change, activation, new acquisition, generation call or acceptance fallback. A cross-subsystem observation is not an atomic snapshot; this limitation is recorded in the receipt.

## Evidence and execution envelope

Only the new private `root-evidence` leaf beneath the exact runner output inode receives privileged files. They are returned to UID 1000 for artifact preservation. The fixed source-pinned bootstrap helper supplies bounded process and evidence utilities; it is unchanged. The root capsule contains only this helper and the inspector, using strict Base64 with byte/hash assertions.

The existing service launch recipe, cgroup resource settings, clean environment, journal transport, 900-second inner alarm, 930-second service lifetime and 115,000-byte code bound are retained. The workflow shares `merlin-dot-oci-operations` concurrency with cancellation disabled. It adds no Avrea trigger.

Expected artifact:

```text
merlin-browser-state-inspection-<run-id>-<attempt>
```

The principal receipt is `root-evidence/state-inspection.json`, accompanied by the selected unit output, source identities, request, exact control log, launch identity and root journal. `inspection_complete` means the permitted observations completed; it does not mean browser acceptance passed. Incomplete observations yield an explicit receipt and nonzero workflow exit. Raw failure artifacts are retained either way.

## Local verification

All **19 focused fixture controls** passed using the exact isolated workflow invocation, with zero errors, failures or skips. They cover missing/present metadata, no-follow symlinks, races and errors, trusted and untrusted marker cases, matching-only socket filtering and bounds, fixed unit arguments, exact request scope and the unconditional prohibition on acceptance.

Source pins and generated Python parse with Python 3.9 grammar. This is static compatibility and local fixture execution, not a native host run. Both Base64 capsules decode to their exact source bytes. The service launch AST matches the corrected acceptance recipe. The assembled root-code fixture is 37,547 bytes, below the unchanged runtime bound; it was not executed.

The 19 diagnostic controls are separate from the existing product test counts. Original failed-run evidence and frozen source maps are preserved. Two independent reviewers found no concrete action-scope or read-boundary blocker in the prepared files. The native diagnostic result remains pending.
