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
8. Before dispatching any CACE Actions job, an agent must verify repository-wide that no CACE job is queued or in progress. Exactly one CACE Actions job may be active or queued at a time.
9. A task lease has one effective owner. Another agent may review it, but may not independently dispatch or mutate the leased task without an explicit valid handoff.
10. SHA-256 is used for content identity/integrity. A digest is never treated as proof of semantic or mathematical correctness.

## Activation and append-only boundary

PR #14 is the bootstrap period for this protocol. Before the protocol's first acceptance into `main`, bootstrap records may be corrected or backfilled by ordinary Git commits while the design is still being established; Git history is the audit trail for those bootstrap edits.

After activation on `main`, accepted collaboration records are append-only. A correction must be a new record with the appropriate `supersedes` relationship; an accepted record is not edited in place.

This bootstrap exception does not upgrade the evidentiary status of any record and does not weaken the exact-head or proof rules.

## Record layout

Records live under `collaboration/records/` as JSON. Each record validates against `collaboration/schema/cace-collaboration-record.schema.json`.

Required fields bind the record to an exact repository state and make its role explicit: `record_id`, `record_type`, `sender`, `target`, `head_sha`, `evidence_class`, `created_at`, `payload`, and `content_sha256`.

`content_sha256` is the SHA-256 of canonical JSON containing every field except `content_sha256`: UTF-8, sorted keys, compact separators (`,` and `:`), and no NaN/Infinity. This makes records content-addressable without claiming that the hash proves the payload.

## Lease ownership and handoff

A `TASK_LEASE` is owned by its `sender`.

A `HANDOFF` transfers ownership on the same exact `head_sha`: its `sender` must be the current effective owner, its `target` is the new effective owner, and it must supersede the current lease/handoff. The target must differ from the current owner.

A later `TASK_LEASE` may refresh an existing lease chain only when its `sender` is already the effective owner. A direct owner change through a new `TASK_LEASE` is invalid; ownership changes require `HANDOFF`.

Each exact head may have at most one unsuperseded lease/handoff chain. One lease/handoff record may be superseded at most once.

## Task lifecycle

A task begins with `TASK_LEASE`. `PROPOSAL` and `REVIEW` records may follow while the lease remains active. A `HANDOFF` may transfer ownership before completion. A `DECISION` records the disposition, and `CLOSED` may follow only after a decision.

Messages such as `PROPOSAL`, `REVIEW`, `DECISION`, and `CLOSED` must refer to the same exact source head as an earlier lease/handoff. Cross-head supersession is forbidden.

## Exact-head authorization

`head_sha` identifies the exact source state being authorized; it does not need to equal the later repository commit that stores a historical record.

Before an agent mutates or dispatches work for an exact source state, it should validate the live lease chain for that source SHA:

```text
python scripts/validate_collaboration_lifecycle.py --authorization-head <40-hex-sha> --actor <agent>
```

Authorization succeeds only when that exact source SHA has one valid live lease/handoff and the requested actor is its effective owner. Historical records for another SHA remain valid history but do not authorize the requested source state.

## Discovery Ledger linkage

A record may contain `discovery_refs` and `evidence_refs`. These are references only. The verifier checks their shape and content hash; domain-specific qualification continues to be enforced by CACE's existing proof/acceptance machinery.

## Agent behavior

ChatGPT, Gemini, local models, and future agents use the same schema. Model identity grants no evidence privilege. Agents should prefer small exact-head tasks, state uncertainty, preserve failed attempts as engineering evidence when useful, and never promote telemetry, correlations, analogies, or AI suggestions beyond `AI_PROPOSAL` without independent evidence.
