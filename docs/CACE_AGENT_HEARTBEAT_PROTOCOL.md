# CACE Agent + Canvas Heartbeat Protocol v1

Status: coordination/observability design only. Heartbeats are never scientific or mathematical evidence.

## Two separate heartbeat channels

1. **Agent heartbeat** — liveness, progress, lease, checkpoint, budgets, blockers.
2. **Semantic canvas heartbeat** — deterministic node/dependency state and compact deltas for UI/local-AI attention.

Example canvas states:
`DORMANT | READY | ACTIVE | WAITING | BLOCKED | STALE | VERIFYING | VERIFIED | FAILED | RESEARCH_INTEREST`

`VERIFIED` may only mirror canonical verification state. AI attention cannot create it.

## Agent heartbeat envelope

A versioned record should include:
- run/task/agent identity;
- monotonic sequence number;
- phase;
- current bounded action;
- last durable progress sequence;
- last checkpoint reference;
- dependency blockers;
- approval-needed flag;
- network mode;
- resource/tool budget snapshot;
- lease deadline;
- timestamp;
- `evidence_authority=false`.

Suggested phases:
`PLANNING | EXECUTING | WAITING | VERIFYING | BLOCKED | PAUSED | COMPLETE | FAILED | CANCELLED`.

## Liveness is not progress

A repeated pulse means only that the worker can emit a pulse. It does not prove useful work, scientific correctness, verification, or theorem completion.

Keep separate:
- liveness event;
- durable progress event;
- checkpoint event;
- canonical verification event.

## Lease/recovery

- heartbeat renews scheduler lease;
- expired lease marks worker unresponsive;
- resume from last durable checkpoint;
- duplicate/out-of-order heartbeat handling is idempotent;
- monotonic sequence state cannot move backward;
- stalled liveness without progress triggers replan/pause/critic review according to policy.

## Loop/runaway detection

Detect repeated action fingerprints, no durable progress, state oscillation, repeated verifier failure without changed premises, budget exhaustion, and dependency deadlock.

## Canvas integration

Hard-dependency semantic-hash changes propagate STALE. Heartbeat deltas can let the local AI focus on changed/blocked/stale nodes without rereading the entire canvas.

Presentation animation never changes semantic hashes or evidence.

## Security

No secrets in heartbeat payloads. Host-observed resource measurements outrank AI self-report. Zero-contact mode may not use heartbeat transport as a network escape. Heartbeats cannot mutate proof/evidence registries.
