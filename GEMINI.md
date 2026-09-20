# Gemini / Google AI Studio Instructions for CACE

This file is the **Gemini-first repository entrypoint** for implementation work. It is implementation governance only; it is not scientific, proof, qualification, or production-readiness evidence.

## Primary rule

> **Gemini is a primary CACE implementation builder. It may work in Presentation Builder mode or Rigorous Tool Builder mode. Scientific/exact kernels belong in C++, orchestration in Python, formal mathematics in Lean, and canonical qualification remains external to AI authority. JavaScript/TypeScript/Node must never become an alternate scientific/proof engine.**

## Gemini operating modes

### 1. Presentation Builder

Build the browser experience against CACE's typed API/core. The browser remains presentation/controller code and may not duplicate scientific/proof semantics.

### 2. Rigorous Tool Builder

Gemini is explicitly allowed to improve CACE's mathematical/scientific core by:

- designing typed tool/module contracts;
- implementing canonical load-bearing algorithms in `cpp/**`;
- writing C++ unit/property/adversarial tests;
- adding thin Python bindings/orchestration where necessary;
- implementing exact/certificate checkers;
- writing Lean theorem statements and proof attempts under `formal/**`;
- implementing explicit runtime-to-formal bindings;
- preparing Help/examples;
- preparing a proof-ready handoff when some formal obligations remain.

Before Rigorous Tool Builder work, read `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`.

If Gemini cannot finish a proof or source-to-formal bridge, it must submit a machine-readable packet conforming to `collaboration/schema/cace-ai-tool-submission.schema.json`, validated by `scripts/validate_ai_tool_submission.py`. Unresolved obligations must remain explicit.

Gemini may reach draft/quarantine/preflight-ready states, but it may not self-declare canonical `FORMAL`/`PASS`. Exact-current-head qualification remains authoritative.

CACE remains layered as:

```text
Browser presentation (Gemini-built React/TypeScript or equivalent)
        |
        | HTTP/typed client
        v
Python API/orchestration boundary: api/index.py + cace_studio/core/**
        |
        +--> C++20 scientific/exact kernels: cpp/**
        |
        +--> canonical claim/proof governance
                    |
                    v
            Lean formal source + external exact-head qualification
            formal/cace_formal/**
```

A Node server created by AI Studio may be used only as a **development/static/proxy surface** when needed by the AI Studio environment. It is not allowed to become an alternate CACE scientific backend.

## Read before editing

**Gemini file-ingestion rule:** read `AI_CONTEXT/00_START_HERE.md`, `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`, and `AI_CONTEXT/PULL_MANIFEST.json` first. CACE plans for a maximum of 800 files per context pull to stay safely below the observed ~1000-file ingestion ceiling. If more files are needed, use deterministic task shards; never continue after silent truncation/discard.

Read these in this order:

1. `CACE_AGENT_BOOTSTRAP.json`
2. `CACE_AI_BUILDER_CONTRACT.md`
3. `docs/GEMINI_AI_STUDIO_HANDOFF.md`
4. `AGENTS.md`
5. `docs/CROSS_CHAT_HANDOFF.md`
6. `docs/BUILD_AND_TRUST_GUIDE.md`
7. `docs/ARCHITECTURE.md`
8. `docs/CONSTITUTION.md`
9. `docs/CLAIMS.md`
10. `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md` when runtime/formal linkage is touched
11. `gemini/CACE_GEMINI_TASK_STATE.json`
12. relevant exact source/tests for the task

Always re-query live GitHub/CI state before acting on a proof or deployment gate. Snapshot documents can be stale.

## What Gemini should own in Presentation Builder mode

Gemini may implement and improve:

- React/TypeScript browser UI;
- drag/drop and click-to-connect graph editing;
- panels, dialogs, keyboard controls, minimap, camera and 3D presentation;
- coordinate-system visualizations that are explicitly presentation-only;
- typed API client code;
- local browser state, autosave, undo/redo and view state;
- accessibility and responsive layout;
- help/documentation UI;
- optional AI-assistant presentation and provider setup UI;
- browser-side formatting of already-returned evidence/status objects;
- tests of presentation behavior and API contract consumption.

## What Gemini must NOT reimplement in JavaScript/TypeScript/Node

Do not create a second implementation of:

- `GraphExecutor` execution semantics;
- scientific modules/solvers/estimators;
- exact FEM/P1/RT0 algebra;
- C++ numerical or exact kernels;
- unit/type compatibility authority;
- certificate validity;
- proof-contract truth;
- claim/proof promotion;
- formal PASS/FAIL/NOT_RUN derivation;
- qualification drift logic;
- theorem metadata or Lean reasoning;
- canonical hashes/attestations whose meaning is defined by the backend;
- source-to-formal bridge semantics.

The browser may display these results. It may not authoritatively derive them.

## Existing web/API boundary

The current backend is `api/index.py`. The existing browser implementation is under `web/`.

Current authoritative API surfaces include:

- `GET /api/health`
- `GET /api/modules`
- `GET /api/claims`
- `POST /api/connections/validate`
- `POST /api/runs`
- `GET /api/runs/{job_id}`
- `POST /api/runs/{job_id}/{pause|resume|cancel}`

When Gemini needs a capability that is not exposed, **extend the Python API/core deliberately** rather than reproducing the missing semantic rule in TypeScript.

For connection validation, the browser should call `POST /api/connections/validate` as the authority. Client-side checks may exist only as immediate UX hints and must never replace backend validation.

For execution, the browser submits an experiment to `POST /api/runs` and consumes the returned run/evidence object. It must not execute scientific modules locally in JavaScript.

For claims/proofs, the browser consumes `GET /api/claims` and related future typed endpoints. It must never synthesize a formal PASS.

## Presentation-only math visualization

Gemini may render Cartesian, hexagonal, Einstein/aperiodic tilings, complex-base/fractal coordinate views, 3D rotations, meshes, fields and other visual representations in the browser when the transform is explicitly a **view**.

If a transform changes scientific computation, topology, numerical values, certificate identity, mesh identity, theorem hypotheses, or result semantics, it is no longer presentation-only and must be implemented through the canonical Python/C++/Lean path.

## C++ / Python / Lean division

- **Python:** orchestration, API, GUI-facing contracts, serialization, provenance plumbing, thin bindings.
- **C++:** load-bearing scientific/exact/high-performance kernels.
- **Lean:** formal mathematical statements/proofs and canonical qualification.
- **JavaScript/TypeScript/React:** presentation and interaction only.

Do not move load-bearing scientific computation into TypeScript because it is convenient for a preview.

## Current concurrent work

Keep Gemini web work isolated from proof-sensitive work.

At the time this handoff was created:

- PR #42: v3.41A proof work on `proof/v3.41a-box-zero-boundary-core`.
- PR #60: C++ exact P1/RT0/FSL runtime work on `feature/cpp-fsl-exact-kernel`.

Do not mix browser refactors into those branches.

## Preferred first Gemini implementation batch

1. Preserve `api/index.py` as the semantic boundary.
2. Add a typed TypeScript API client for the existing endpoints.
3. Build a React/TypeScript shell with feature parity for the current `web/` editor.
4. Route connection validation to the backend.
5. Route run/start/status/pause/resume/cancel to the backend.
6. Render canonical claims/evidence read-only from backend payloads.
7. Add UI tests that prove the browser does not silently invent successful verification.
8. Keep any AI Studio Node layer as a thin proxy/dev layer only.

Do **not** delete the current vanilla browser implementation until the new presentation layer has feature-parity and integration tests.

## Required handoff after each Gemini batch

Report:

- changed files;
- change class A-E from `CACE_AI_BUILDER_CONTRACT.md`;
- backend/API contracts consumed or changed;
- tests run and results;
- scientific/evidence semantics impact;
- qualification-sensitive files changed: yes/no;
- unresolved obligations;
- recommended next gate.

If the answer to “qualification-sensitive files changed” is yes, stop treating the batch as ordinary web work and follow the formal workflow.


## Agent Perception Packet

For Local AI / canvas integration, consume the typed perception stream in `schema/cace-agent-perception.schema.json`.

This stream gives the agent compact live experiment deltas—active/blocked/stale/verifying state, residual/convergence trend, resource pressure, blockers, canonical evidence snapshots, and research-interest—so it can react to the evolving canvas without rereading the entire experiment.

Treat this as non-evidentiary perception/coordination data. It cannot promote proof or scientific evidence.
