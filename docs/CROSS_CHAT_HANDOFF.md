# CACE Cross-Chat Handoff

Status: continuity/navigation document only. It is **not proof, qualification, production-readiness, or scientific evidence**.

Last refreshed: 2026-09-19.

## Standing continuity directive

Every CACE chat or connected agent should be able to continue without asking the user to reconstruct prior work from memory.

For every new CACE chat:

1. Retrieve this file and `docs/CHAT_IDEA_LEDGER.md`.
2. If ChatGPT Library access is available, search for the mirrored files:
   - `/CACE CONTINUITY/CACE_CROSS_CHAT_HANDOFF.md`
   - `/CACE CONTINUITY/CACE_CHAT_IDEA_LEDGER.md`
3. Read `CACE_AGENT_BOOTSTRAP.json`, `docs/GOAL_REGISTRY.json`, and the relevant current proof/feature roadmap.
4. Re-query live GitHub branch, PR, commit, and Actions state before taking any proof/deployment action. A snapshot in this file may be stale.
5. Continue from the highest-value live gate without asking the user to repeat already-preserved context.

For every substantive CACE chat before a natural stopping point:

1. identify new user ideas/goals with mathematical, scientific, product, reliability, proof-rigor, security, visualization, AI, deployment, or workflow merit;
2. deduplicate them against `docs/GOAL_REGISTRY.json` and `docs/CHAT_IDEA_LEDGER.md`;
3. append specific novel ideas to the idea ledger;
4. update the goal registry/master spec when the idea changes durable implementation intent;
5. refresh the exact live handoff state when a proof/CI/deployment gate changes;
6. mirror the current handoff and idea ledger to ChatGPT Library when available;
7. never convert documentation, AI agreement, historical logs, or a handoff snapshot into proof evidence.

This is a standing CACE workflow preference.

## Source-of-truth hierarchy

Use this order rather than treating the handoff as authority:

- current checked-out / queried Git commit for source;
- `formal/cace_formal/` for formal statements;
- `cace_studio/data/claim_registry.json` and `cace_studio/data/proof_ledger.json` for canonical formal claim status;
- exact-current-head Actions/qualification artifacts for proof qualification evidence;
- `docs/GOAL_REGISTRY.json` and `docs/MASTER_BUILD_SPEC.md` for durable implementation intent;
- `docs/CHAT_IDEA_LEDGER.md` for preserved research/product ideas that may not yet be scheduled;
- this file for continuity and next-step navigation.

## Redundant preservation surfaces

### 1. GitHub repository

Canonical continuity files:

- `docs/CROSS_CHAT_HANDOFF.md`
- `docs/CHAT_IDEA_LEDGER.md`
- `docs/GOAL_REGISTRY.json`
- `docs/MASTER_BUILD_SPEC.md`
- `CACE_AGENT_BOOTSTRAP.json`

### 2. ChatGPT Library

Mirror the two self-contained continuity documents under:

`/CACE CONTINUITY/`

This is the primary cross-chat fallback if GitHub is unavailable to a future chat.

Operational mirror status (2026-09-19): the `/CACE CONTINUITY/` Library folder was created, but this session's generated-file upload bridge returned `container_session_unavailable`, so **do not assume the two current mirror files are present yet**. The exact current files remain in GitHub and in the generating chat as downloadable artifacts. A future CACE chat with a working Library write surface should retry the mirror and then update this status.

### 3. Existing historical Library corpus

Useful recovery sources include:

- `CACE_MASTER_TIMELINE_FEATURES_MATH_PROOFS_IDEAS_2026-09-17.txt`
- `CACE_FULL_REMAINING_PLAN_2026-09-14.txt`
- `CACE_EXACT_CONTINUATION_HANDOFF_2026-09-16.txt`
- `CACE_PROGRAM_GOALS_STATUS_2026-09-16.txt`
- `INFINITE_EXTENSION.md`
- `THEORY.md`

These are historical/context sources only; current code/proof status must be re-verified.

## Current proof handoff snapshot

Snapshot timestamp: 2026-09-19 20:11 UTC. **Re-query live state before acting.**

### Durable CI infrastructure

PR #47, “CI: batch quarantined theorem preflight to minimize user dispatches”, was merged to `main`.

Merged commit:

`7c3bbe8cc744b9ed9c7ead6f1a5fdf308e790b1c`

Durable behavior includes:

- batched quarantined theorem preflight;
- self-validating Lean-source sanity;
- required sentinel scanning;
- stronger standalone-quarantine protections;
- regression-tested CACE Actions serialization;
- provider-independent local evidence retention for source-sanity runs.

### Current formal theorem batch

Roadmap:

`docs/proofs/V341_TOP20_OF50_THEOREM_ROADMAP.md`

Partition:

- v3.41A ranks 1–8
- v3.41B ranks 9–14
- v3.41C ranks 15–16
- v3.41D ranks 17–19
- v3.41E rank 20

v3.41A branch:

`proof/v3.41a-box-zero-boundary-core`

Current promoted head:

`f13b63c02c74209f3e47a88ab11ed7b4a1e33c72`

PR:

#42 — “Draft: v3.41A construct smooth box zero-boundary core”

Standalone Exact-Pin passed earlier on pre-promotion head:

`4465586eff2c606ebcfb0fbc11c853ea6ddc88f5`

Audited-root Exact-Pin run:

`35466492951`

Result: **SUCCESS** at exact head `f13b63c02c74209f3e47a88ab11ed7b4a1e33c72`.

The successful audited-root run passed:

- exact-head isolation;
- serialization;
- requested-target/root reachability;
- permanent proof guardrails and frozen plan;
- malformed-source rejection;
- pinned Lean/Mathlib restore;
- cache-local verification;
- proof API canaries;
- impacted-module and reverse-dependent compilation;
- requested `BoxZeroBoundaryCore` compilation;
- frozen-plan recheck;
- full audited-root compilation;
- aggregate diagnostic gate;
- evidence upload.

### v3.41A mathematical scope

Implemented/promoted module:

`CACEFormal/BoxZeroBoundaryCore.lean`

It constructs an explicit smooth face-vanishing scalar core and proves the corresponding zero classical face flux / normal-trace pairing for smooth vector fields.

Preserve these nonclaims:

- it does **not** yet extend the cancellation to every closed-graph H(div) test;
- it does **not** identify the graph closure with every textbook presentation of H_0^1;
- it does **not** prove arbitrary box H1 fields have zero trace;
- documentation or successful preflight alone is not canonical formal qualification.

### Next formal gate

Before beginning v3.41B promotion, perform the normal **canonical exact-current-head qualification** for the v3.41A promoted head and verify the emitted kernel/metadata/proof-contract/provenance evidence.

If canonical qualification passes, preserve/promote exact provenance and then proceed to v3.41B ranks 9–14:

- fixed-test-field normal-trace continuous functional;
- dense-flux-core annihilation -> functional zero boundary trace;
- embedded smooth face-vanishing scalar -> functional zero trace;
- smooth-to-closed H1 graph linear map;
- concrete boundary-vanishing smooth graph core;
- core inclusion in the functional zero-boundary submodule.

## CI / proof operating rules

- Do cheap/static/local checks before spending an OCI Lean run.
- Serialize expensive CACE proof jobs.
- Do not retry unchanged failures.
- Convert each discovered failure class into a regression guard where practical.
- Cache work, never truth.
- Do not weaken theorem statements, proof scope, negative tests, or canonical gates to get green CI.
- Prefer batched standalone proof preflight for multiple quarantined modules when rigor is unchanged.
- Exact-current-head canonical qualification remains separate from preflight.

## Cross-chat update rule

A future CACE chat that materially changes any of the following should refresh this handoff:

- active theorem/proof frontier;
- exact head/PR/run IDs;
- current deployment gate;
- durable architecture;
- new meritorious user goals;
- novel mathematical/research ideas;
- CI/proof safety rules;
- major feature completion or removal.

The goal is continuity without making conversational memory part of the trusted computing base.


## New local-AI reasoning direction

Added 2026-09-19.

Design document:

`docs/LOCAL_AI_REASONING_CURRICULUM.md`

New durable goals:

- G048 — reasoning-first local AI curriculum and anti-memorization evaluation;
- G049 — Conway-inspired canvas/local-AI heartbeat field.

Core intent:

- teach reusable typed operations and operation order rather than memorized answers;
- procedural generation + held-out structural compositions;
- canonical/load-bearing perturbation pairs where answers must change;
- irrelevant/symmetry perturbations where answers must remain invariant;
- external executable operator-plan checks rather than hidden chain-of-thought dependence;
- geometric/relational structure, invariants and sparse operator programs rather than brute-force all-pairs association;
- deterministic canvas heartbeat states that guide AI attention but can never promote verification.
