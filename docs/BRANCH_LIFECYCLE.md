# CACE Branch Lifecycle Policy

Status: repository coordination policy. Not scientific/proof evidence.

Canonical machine-readable source: `BRANCH_LIFECYCLE.json`.

## Non-negotiable rule

> **A Git branch existing on GitHub does not mean an agent may use it. Only branches explicitly classified `ACTIVE` in `BRANCH_LIFECYCLE.json` are writable by default.**

Before creating commits, rebasing, opening a PR, or using an old branch as a base, every agent must inspect the lifecycle registry.

## Status meanings

| Status | New agent work? | Meaning |
|---|---:|---|
| `ACTIVE` | **Yes** | Current assigned development branch. |
| `INTEGRATION` | No | Canonical base/integration branch; direct writes require explicit instruction. |
| `FROZEN` | No | Preserved work/PR. Inspect/compare only unless explicitly reactivated. |
| `DEPRECATED` | **Never by default** | Superseded. Do not extend, branch from, or merge as current work. |
| `ARCHIVED` | **Never by default** | Historical snapshot/evidence only. |
| `REVIEW_REQUIRED` | No | Unclassified. Stop and classify before using. |

## Resolution order

Branch status is resolved in this order:

1. exact entry in `explicit_branches`;
2. matching lifecycle pattern;
3. `default_status = REVIEW_REQUIRED`.

Exact entries always win over patterns.

## Current writable branch

At the time of this policy:

- `feature/local-agent-tool-bus-v1` — **ACTIVE**, PR #79.

`main` is the canonical integration branch but is intentionally `INTEGRATION`, not `ACTIVE`. Agents should not push directly to `main` unless the user explicitly requests that workflow.

## Open PR branches

Most currently open PR heads are recorded as `FROZEN`.

This is intentional. CACE has accumulated many parallel historical proof, science, UI, and architecture branches. Leaving the PR open preserves context; it does **not** authorize an agent to resume that branch automatically.

When the user explicitly chooses one of those PRs as current work, update `BRANCH_LIFECYCLE.json` first:

- make that branch `ACTIVE`;
- freeze the previously active branch if appropriate;
- record the reason/date/PR.

## Deprecated branches

Deprecated branches remain on GitHub only for traceability until deliberate cleanup.

Agents must not:

- checkout a deprecated branch as their working base;
- create new commits on it;
- create a new branch from it;
- cherry-pick it wholesale into current work;
- launch CI from it as if it were current;
- cite its historical success as current-head qualification.

If a valuable commit exists only on a deprecated branch, recover that **specific commit/file intentionally** into an active branch, with tests and current-head validation.

## Archived branches

Archived branches are immutable historical references such as backup/release snapshots.

Do not update them.

## Unknown branches

Unknown branches fail closed to `REVIEW_REQUIRED`.

An agent encountering one must not guess whether it is current. Inspect:

- open/closed PR status;
- merge ancestry;
- current architecture/proof handoff;
- newer superseding branches;
- this registry.

Then update the registry before using it.

## Cleanup discipline

Whenever a branch/PR is merged, abandoned, or superseded:

1. update `BRANCH_LIFECYCLE.json`;
2. add/adjust an explicit supersession reason when important;
3. update `docs/BRANCH_LIFECYCLE.md` only if the policy itself changed;
4. avoid deleting branches that still serve as proof/provenance references until their archival role is understood.

## Agent startup checklist

Before repository edits:

1. read `AGENTS.md`;
2. read `BRANCH_LIFECYCLE.json`;
3. resolve the requested branch status;
4. verify the live GitHub branch head;
5. refuse accidental work on non-`ACTIVE` branches;
6. preserve exact-head/proof qualification rules separately.

This branch registry is coordination metadata only. It does not establish scientific correctness or proof qualification.


## Proof-submission branches

Controlled proof submissions use the namespace:

`submission/proof/<submission-id>`

The submission service may create the initial commit/draft PR as a narrowly scoped system action. After that initial handoff, the branch is `FROZEN` for general coding agents.

Agents may inspect the branch and its CI, but may not continue implementation on it unless the operator explicitly reactivates it for a review-fix cycle.

See `docs/PROOF_SUBMISSION_REVIEW_WORKFLOW.md`.
