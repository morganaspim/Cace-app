# CACE AI Collaboration / Repository Coordination Protocol

Status: engineering coordination protocol; it is not proof evidence.

Qualified baseline: `ce2487e2a7b85c095e0926b11c97fc1c4eba5de8`, canonical qualification run 44 (`35204273914`).

## Invariants

1. Every task and message names an exact lowercase 40-hex Git commit SHA.
2. A record authorizes work only for the exact `head_sha` carried by its live lease chain. Records for other heads remain historical evidence and never silently authorize a newer or different source state.
3. Accepted coordination records are append-only after protocol activation. Corrections create a new record referring to the superseded record.
4. AI agreement is never mathematical proof. Evidence class may only increase when the referenced evidence independently justifies it.
5. Allowed evidence classes are `AI_PROPOSAL`, `ENGINEERING_VERIFIED`, `CERTIFIED_NUMERICAL`, and `PROVED`.
6. `PROVED` requires a named kernel-checked theorem/evidence artifact and exact qualified source identity; prose or model consensus cannot set it.
7. `CERTIFIED_NUMERICAL` requires a rigorous numerical/error certificate with stated assumptions and bounds.
8. Before dispatching any CACE Actions job, or mutating a branch/PR/ref in a way that can trigger a CACE Actions workflow, an agent must verify repository-wide that no CACE job is queued or in progress. Exactly one CACE Actions job may be active or queued at a time.
9. A task lease has one effective owner. Another agent may review it, but may not independently dispatch or mutate the leased task without an explicit valid handoff.
10. SHA-256 is used for content identity/integrity. A digest is never treated as proof of semantic or mathematical correctness.

## Activation and append-only boundary

PR #14 is the bootstrap period for this protocol. Before the protocol's first acceptance into `main`, bootstrap records may be corrected or backfilled by ordinary Git commits while the design is still being established; Git history is the audit trail for those bootstrap edits.

After activation on `main`, accepted collaboration records are append-only. A correction must be a new record with the appropriate `supersedes` relationship; an accepted record is not edited in place.

This bootstrap exception does not upgrade the evidentiary status of any record and does not weaken the exact-head or proof rules.

## Record layout and canonical order

Records live under `collaboration/records/` as JSON. Each record validates against `collaboration/schema/cace-collaboration-record.schema.json`.

Required fields bind the record to an exact repository state and make its role explicit: `record_id`, `record_type`, `sender`, `target`, `head_sha`, `evidence_class`, `created_at`, `payload`, and `content_sha256`.

`content_sha256` is the SHA-256 of canonical JSON containing every field except `content_sha256`: UTF-8, sorted keys, compact separators (`,` and `:`), and no NaN/Infinity. This makes records content-addressable without claiming that the hash proves the payload.

Canonical record order is lexicographic filename order. Persisted record filenames begin with an 8-digit ordinal followed by `-`; later records use a strictly larger ordinal. `created_at` must be timezone-aware and nondecreasing in canonical record order. Any `supersedes` reference must point to an earlier record in that same order.

These ordering rules make lifecycle evaluation deterministic. They do not make timestamps or filenames proof evidence.

## Supersession and corrections

Lease-chain supersession and message correction are intentionally distinct.

A `TASK_LEASE` or `HANDOFF` may supersede only an earlier `TASK_LEASE` or `HANDOFF` on the same exact `head_sha`, subject to the ownership rules below. Lease-chain supersession changes which owner is live.

A non-lease record (`PROPOSAL`, `REVIEW`, `DECISION`, or `CLOSED`) may supersede only an earlier record of the same `record_type`, on the same exact `head_sha`, from the same `sender`. This is an append-only correction relation; it does not alter lease ownership. A record may be superseded at most once.

Cross-head supersession is forbidden. A correction by a different agent is not a correction of the original author's record; that agent should use an appropriate `REVIEW` or `DECISION` record instead.

## Lease ownership and handoff

A `TASK_LEASE` is owned by its `sender`.

A `HANDOFF` transfers ownership on the same exact `head_sha`: its `sender` must be the current effective owner, its `target` is the new effective owner, and it must supersede the current lease/handoff. The target must differ from the current owner.

A later `TASK_LEASE` may refresh an existing lease chain only when its `sender` is already the effective owner. A direct owner change through a new `TASK_LEASE` is invalid; ownership changes require `HANDOFF`.

Each exact head may have at most one unsuperseded lease/handoff chain.

## Task lifecycle

A task begins with `TASK_LEASE`. `PROPOSAL` and `REVIEW` records may follow while the task remains open. A `HANDOFF` may transfer ownership before completion.

A `DECISION` records the disposition. After a decision, new lease refreshes, handoffs, proposals, and reviews for that task are invalid. `CLOSED` may follow only after a decision.

After `CLOSED`, no new lifecycle activity is valid except append-only same-type corrections to an earlier message record. At most one effective `DECISION` and one effective `CLOSED` record may remain after correction chains are applied.

Messages such as `PROPOSAL`, `REVIEW`, `DECISION`, and `CLOSED` must refer to the same exact source head as an earlier lease/handoff.

## Exact-head authorization

`head_sha` identifies the exact source state being authorized; it does not need to equal the later repository commit that stores a historical record.

Before an agent mutates or dispatches source work for an exact source state, it should validate the live lease chain for that source SHA:

```text
python scripts/validate_collaboration_lifecycle.py --authorization-head <40-hex-sha> --actor <agent>
```

Authorization succeeds only when that exact source SHA has one valid live lease/handoff, the requested actor is its effective owner, and the task has no effective `DECISION` or `CLOSED` record. Historical records for another SHA remain valid history but do not authorize the requested source state.

The authorization check governs source mutation/dispatch. Append-only coordination bookkeeping needed to record a decision, closure, or correction is validated by the lifecycle rules themselves.

## Actions serialization boundary

The executable CACE Actions surface is intentionally small. Every active self-hosted CACE workflow must use the same repository-wide concurrency group with `cancel-in-progress: false`; `scripts/audit_cace_actions_policy.py` fails closed if the admitted workflow set, automatic-trigger set, concurrency group, or cancellation policy drifts.

GitHub concurrency serializes execution but can retain a pending run. Therefore the stronger CACE invariant—no second CACE run may even be queued while another is queued or in progress—is enforced before the trigger is created: agents must perform the repository-wide lane-clear check before explicit dispatch and before any branch/PR/ref mutation that can cause an automatic CACE workflow run. The in-job serialization guard is a second fail-closed check, not a substitute for this pre-trigger rule.

Historical workflow definitions that are not part of the admitted active surface are retained under `.github/workflow-archive/`. Moving one back into `.github/workflows/` requires policy review before it becomes executable.

## Discovery Ledger linkage

A record may contain `discovery_refs` and `evidence_refs`. These are references only. The verifier checks their shape and content hash; domain-specific qualification continues to be enforced by CACE's existing proof/acceptance machinery.

## Agent behavior

ChatGPT, Gemini, local models, and future agents use the same schema. Model identity grants no evidence privilege. Agents should prefer small exact-head tasks, state uncertainty, preserve failed attempts as engineering evidence when useful, and never promote telemetry, correlations, analogies, or AI suggestions beyond `AI_PROPOSAL` without independent evidence.


## Rigorous tool submission packets

An AI agent that creates or extends a mathematical/scientific CACE tool may attach a rigorous-tool submission packet to a normal `PROPOSAL` collaboration record.

The inner packet must conform to:

`collaboration/schema/cace-ai-tool-submission.schema.json`

and may be validated with:

```text
python scripts/validate_ai_tool_submission.py <submission.json>
```

The packet records the exact source head, C++ files/tests, formal proof state, proposed Lean theorem names/files, source-to-formal references, checks completed, unresolved obligations, and the recommended next proof/engineering gate.

The packet deliberately has `promotion_authority=false`, and its formal state enum does not contain `FORMAL_PASS`. A packet therefore cannot promote a claim; it can only make work reviewable and handoff-ready.

A fully proved-looking AI submission still requires the ordinary CACE proof path and canonical qualification before formal promotion.
