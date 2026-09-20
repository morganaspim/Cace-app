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


## Agent Perception Packet — giving the AI a live sense of the canvas

The Local AI should receive a compact, versioned experimental state stream conforming to:

`schema/cace-agent-perception.schema.json`.

The purpose is to let the agent continuously perceive meaningful change without rereading the full graph. A packet may contain, per node:

- semantic hash and whether it changed;
- heartbeat state;
- residual magnitude when available;
- residual trend: improving/stable/worsening/unknown;
- convergence progress when defined;
- host-measured resource pressure;
- dependency blockers;
- canonical evidence-state snapshot;
- artifact references;
- a non-evidentiary research-interest score.

This acts like a **sensory layer for the experiment**: the agent can notice a residual worsening, a solver becoming blocked, a proof obligation becoming stale, or a new result appearing and decide what to inspect next.

Important separation:

```text
perception / heartbeat
        -> attention / planning / scheduling
        -> tool request / experiment proposal
        -> canonical computation or verifier
        -> evidence state
```

The arrow never runs backward: attention, excitement, research-interest, convergence heuristics, or repeated heartbeats cannot manufacture evidence.

Only emit `VERIFIED` heartbeat state when mirroring an authoritative verified state from the canonical subsystem. Otherwise use the appropriate nonverified state.
