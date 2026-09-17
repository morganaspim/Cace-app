# CACE AI Collaboration / Repository Coordination Protocol

Status: engineering coordination protocol; it is not proof evidence.

Qualified baseline: `ce2487e2a7b85c095e0926b11c97fc1c4eba5de8`, canonical qualification run 44 (`35204273914`).

## Invariants

1. Every task and message names an exact 40-hex Git commit SHA.
2. A message whose `head_sha` differs from the task lease `head_sha` is stale and must be rejected, not silently rebased.
3. Coordination records are append-only. Corrections create a new record referring to the superseded record.
4. AI agreement is never mathematical proof. Evidence class may only increase when the referenced evidence independently justifies it.
5. Allowed evidence classes are `AI_PROPOSAL`, `ENGINEERING_VERIFIED`, `CERTIFIED_NUMERICAL`, and `PROVED`.
6. `PROVED` requires a named kernel-checked theorem/evidence artifact and exact qualified source identity; prose or model consensus cannot set it.
7. `CERTIFIED_NUMERICAL` requires a rigorous numerical/error certificate with stated assumptions and bounds.
8. Before dispatching any CACE Actions job, an agent must verify repository-wide that no CACE job is queued or in progress. Exactly one CACE Actions job may be active or queued at a time.
9. A task lease has one owner. Another agent may review it, but may not independently dispatch or mutate the leased task without a recorded handoff.
10. SHA-256 is used for content identity/integrity. A digest is never treated as proof of semantic or mathematical correctness.

## Record layout

Records live under `collaboration/records/` as JSON. Each record validates against `collaboration/schema/cace-collaboration-record.schema.json`.

Required fields bind the record to an exact repository state and make its role explicit: `record_id`, `record_type`, `sender`, `target`, `head_sha`, `evidence_class`, `created_at`, `payload`, and `content_sha256`.

`content_sha256` is the SHA-256 of canonical JSON containing every field except `content_sha256`: UTF-8, sorted keys, compact separators (`,` and `:`), and no NaN/Infinity. This makes records content-addressable without claiming that the hash proves the payload.

## Task lifecycle

`TASK_LEASE` -> zero or more `PROPOSAL` / `REVIEW` records -> `DECISION` -> optional `HANDOFF` -> `CLOSED`.

A reviewer records accept/modify/reject in a new `DECISION`; existing records are not edited. A stale-head record is retained as historical evidence but cannot authorize current-head work.

## Discovery Ledger linkage

A record may contain `discovery_refs` and `evidence_refs`. These are references only. The verifier checks their shape and content hash; domain-specific qualification continues to be enforced by CACE's existing proof/acceptance machinery.

## Agent behavior

ChatGPT, Gemini, local models, and future agents use the same schema. Model identity grants no evidence privilege. Agents should prefer small exact-head tasks, state uncertainty, preserve failed attempts as engineering evidence when useful, and never promote telemetry, correlations, analogies, or AI suggestions beyond `AI_PROPOSAL` without independent evidence.
