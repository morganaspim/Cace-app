# CACE AI Rigorous Tool Contribution Pipeline

Status: implementation/governance contract. This document is not proof or qualification evidence.

## Goal

Gemini, Antigravity, local agents, and future coding agents may improve CACE by creating new rigorous mathematical/scientific tools, not only UI code.

The preferred path is:

```text
idea / Research Idea
  -> typed tool specification
  -> C++ canonical implementation
  -> unit/property/adversarial tests
  -> exact/certified checker where applicable
  -> Python binding/orchestration
  -> Lean statement + proof attempt
  -> runtime-to-formal binding obligations
  -> quarantine / Exact-Pin preflight
  -> audited promotion
  -> canonical exact-current-head qualification
  -> formally connected production module
```

An AI builder may perform as many of these stages as it can correctly complete. It must never hide an unfinished stage.

## Two valid outcomes

### Outcome A — complete engineering + formal contribution

The agent supplies:
- canonical C++ implementation;
- tests and negative tests;
- typed Python/API bindings only where needed;
- exact/certificate checker when appropriate;
- Lean theorem statement and proof;
- explicit runtime-to-Lean representation bridge;
- all source-to-formal obligations;
- documentation/help/example updates;
- a submission packet saying the work is ready for the next proof gate.

Even then, the AI does not self-promote the result to FORMAL. Canonical qualification remains separate.

### Outcome B — proof-ready submission for another agent/human

If the AI cannot finish the proof or source-to-formal bridge, it must still leave a useful, machine-readable packet containing:
- exact source head;
- semantic tool ID and purpose;
- C++ files and tests;
- assumptions and failure modes;
- exact/certified checks already completed;
- proposed Lean theorem statements/names;
- attempted proof files, if any;
- unresolved proof obligations;
- counterexamples/failed attempts discovered;
- source-to-formal binding questions;
- recommended next proof gate.

This is a successful contribution when the engineering is sound and the missing proof work is explicit.

## Tool construction contract

Every new rigorous tool should define:

- semantic module/tool ID;
- mathematical domain and codomain;
- exact input/output types;
- units where relevant;
- assumptions/preconditions;
- deterministic semantics;
- failure modes;
- numerical tolerance only when the tool is numerical;
- evidence capability;
- serialization/content identity;
- independent tests;
- adversarial tests;
- Help metadata and at least one runnable example before production maturity.

Load-bearing exact/high-performance algorithms belong in C++.

Python should remain thin orchestration/bindings.

JavaScript/TypeScript may expose the tool in the browser but may not reimplement it.

## Formalization contract

When a tool is intended to become formally connected, the agent should try to supply:

1. a precise Lean object corresponding to the runtime object;
2. exact/generated serialization or an explicit abstraction relation;
3. theorem hypotheses;
4. proof of representation invariants;
5. theorem statement/proof;
6. binding from runtime packet to theorem hypotheses;
7. negative examples showing near-looking but invalid runtime packets fail;
8. qualification-sensitive file list.

Follow `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md`.

A generic Lean theorem plus a numerically similar C++ computation is not a source-to-formal bridge.

## Submission location

Use an existing CACE collaboration `PROPOSAL` record and place a payload conforming to:

`collaboration/schema/cace-ai-tool-submission.schema.json`.

This preserves exact-head identity, sender/target, evidence class, content hashing, lease ownership, review, decision, and handoff through the existing collaboration protocol.

Validate the packet with:

```bash
python scripts/validate_ai_tool_submission.py path/to/submission.json
```

A tool submission packet is coordination metadata. It is not proof evidence.

## Promotion ladder

Recommended stages:

```text
AI_PROPOSAL
  -> ENGINEERING_VERIFIED
  -> EXACT/CERTIFIED evidence where applicable
  -> Lean draft
  -> QUARANTINED
  -> Exact-Pin preflight
  -> audited promotion
  -> audited-root Exact-Pin
  -> canonical qualification
  -> FORMAL presentation allowed by canonical claim/proof gate
```

No AI-authored field can skip this ladder.

## Heartbeat/perception integration

While an experiment is running, the Local AI should consume the versioned perception stream defined by:

`schema/cace-agent-perception.schema.json`

and `docs/CACE_AGENT_HEARTBEAT_PROTOCOL.md`.

This gives the agent a compact live view of:
- which nodes are active/blocked/stale/verifying;
- residual/convergence trends;
- changed semantic hashes;
- resource pressure;
- dependency blockers;
- canonical evidence state snapshots;
- research-interest signals.

This is the AI's live **experimental state stream**. It is not a substitute for data, certificates, or proof.


## Capability-gap intake from users

The Research Assistant may create a structured Tool Request when a user asks
for a capability that the real CACE registry does not provide.

Canonical intake:

```text
user request
 -> registry confirms capability is absent/incomplete
 -> offer Request this capability / Send feedback
 -> structured Tool Request
 -> engineering triage
 -> Gemini/local Rigorous Tool Builder
 -> cace-ai-tool-submission-v1
 -> ordinary engineering/formal promotion ladder
```

The assistant should preserve the user's motivating experiment and desired
connections, but should not upload private research data by default.

Tool-request popularity may influence engineering priority. It can never
strengthen mathematical evidence.

When the builder changes a tool that already has qualified formal coverage, it
must treat the old runtime-to-formal binding as potentially stale and either
show that the existing theorem/binding still applies or submit updated Lean and
binding obligations. No implementation change inherits FORMAL status merely
because an older version was qualified.
