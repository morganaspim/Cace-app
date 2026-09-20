# Google AI Studio / Gemini Web Integration Handoff

> **Scope note:** This document governs Gemini's browser/presentation work. Gemini also has an explicit **Rigorous Tool Builder** mode for C++ kernels, tests, Lean proof attempts, and source-to-formal bindings. For that mode, follow `GEMINI.md` and `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`. This web handoff does not prohibit rigorous core work.

Status: implementation handoff. **Not verification evidence.**

## 1. Integration decision

Google AI Studio / Gemini is the preferred implementation environment for the CACE browser experience.

The integration contract is intentionally asymmetric:

> **Gemini owns the web presentation layer. CACE's typed Python API/core, C++ kernels, and Lean qualification pipeline own scientific and evidence semantics.**

The browser is a view/controller. It is not a second scientific runtime.

## 2. Target topology

```text
Google AI Studio / Gemini
        |
        | generates/edits
        v
React + TypeScript presentation
        |
        | typed HTTP calls
        v
CACE FastAPI boundary (api/index.py)
        |
        +----------------------+-----------------------+
        |                      |                       |
        v                      v                       v
cace_studio/core/**     cace_studio/modules/**   claim/proof governance
        |                      |                       |
        +----------+-----------+                       |
                   |                                   |
                   v                                   v
            C++20 runtime                          Lean source
               cpp/**                         formal/cace_formal/**
                   |                                   |
                   +--------- evidence remains --------+
                              fail-closed
```

If AI Studio needs a Node server for preview/build mechanics, the allowed topology is:

```text
React -> optional thin Node dev proxy -> CACE FastAPI -> core/C++/Lean-governed state
```

The Node layer must contain no scientific solver, proof, evidence, certificate, or claim-promotion logic.

## 3. Existing backend that the new UI must consume

Canonical browser/API boundary: `api/index.py`.

Existing endpoints:

| Endpoint | Role | Authority |
|---|---|---|
| `GET /api/health` | service health | backend |
| `GET /api/modules` | typed module catalog | backend |
| `GET /api/claims` | canonical claim/proof views | backend |
| `POST /api/connections/validate` | type/unit connection validation | backend |
| `POST /api/runs` | run full graph or selected+upstream | backend |
| `GET /api/runs/{job_id}` | run state/results | backend |
| `POST /api/runs/{job_id}/{action}` | pause/resume/cancel | backend |

The current browser code is:

- `web/index.html`
- `web/studio.css`
- `web/studio.js`

Those files are a behavior reference during migration. They are not a requirement to keep vanilla JavaScript forever.

## 4. Semantic ownership matrix

| Capability | Browser/React | Python core/API | C++ | Lean/qualification |
|---|---:|---:|---:|---:|
| layout/theme/accessibility | OWNER | | | |
| pan/zoom/3D camera | OWNER | | | |
| drag/drop interaction | OWNER | validates serialized graph | | |
| undo/redo/autosave | OWNER | | | |
| module catalog rendering | renders | OWNER | | |
| connection validity | hint only | OWNER | | |
| graph execution | submit/control only | OWNER/orchestrates | kernels | |
| scientific algorithms | | orchestrates | OWNER where load-bearing | theorem scope only |
| exact P1/RT0 math | display only | thin binding | OWNER | formal counterpart |
| certificate/evidence state | render only | OWNER | checker inputs where applicable | qualified formal evidence |
| formal PASS/FAIL/NOT_RUN | render only | OWNER fail-closed gate | | OWNER source/qualification |
| theorem proof | | | | OWNER |
| coordinate visualization | OWNER when view-only | owns semantic transforms | kernels if needed | proof if claimed |
| local AI UI | OWNER | provider policy/orchestration | | never evidence |

## 5. Hard anti-duplication rules

Gemini must not:

1. port C++ scientific kernels into TypeScript for convenience;
2. port Lean theorems into TypeScript predicates and call them proofs;
3. duplicate `GraphExecutor` semantics in the browser;
4. duplicate backend unit/type rules as the final authority;
5. infer formal status from module labels;
6. convert missing/NOT_RUN verification into success;
7. compute a client-side “proof passed” flag;
8. reinterpret floating point as exact rational equality;
9. let an AI-generated answer mutate claim/proof truth;
10. let UI state alter canonical evidence without a backend action.

Client-side prechecks are allowed for responsiveness only when the backend repeats the authoritative check.

## 6. Typed frontend contract

The preferred browser implementation should create one narrow TypeScript client module, for example:

`webapp/src/api/caceClient.ts`

The rest of the UI should depend on that client rather than calling `fetch` ad hoc.

Recommended type groups:

- `ModuleDescriptor`
- `PortDescriptor`
- `Experiment`
- `ExperimentNode`
- `ExperimentEdge`
- `ExperimentGroup`
- `ConnectionValidation`
- `RunRequest`
- `RunSnapshot`
- `VerificationRecord`
- `ClaimView`

Do not invent fields that look like proof/evidence truth. Reflect backend payloads exactly.

A later backend batch may expose OpenAPI-derived client types, but generated types are not a reason to relocate semantics into the browser.

## 7. Recommended migration path

### Batch GWEB-1 — typed client + shell

- create the React/TypeScript app;
- add the typed CACE API client;
- implement health/module/claim loading;
- keep current `web/` available as fallback;
- no scientific changes.

### Batch GWEB-2 — graph editing parity

Implement:

- module library/search;
- drag/drop;
- click-to-connect;
- node property editing;
- selection/multiselect/delete;
- groups;
- undo/redo/copy/paste;
- pan/zoom/fit/minimap;
- save/open/autosave.

Connection attempts must be confirmed by the backend validation endpoint.

### Batch GWEB-3 — execution/evidence parity

Implement:

- run graph;
- selected + upstream;
- GPU policy toggle as a request parameter only;
- pause/resume/cancel;
- run status;
- evidence/claim panels.

The browser must detach stale run evidence whenever semantic graph state changes, while the backend remains the final authority.

### Batch GWEB-4 — CACE-specific advanced visualization

Add view-only:

- 2D/3D switching;
- drag-to-rotate;
- Cartesian/grid views;
- hexagonal and other tiling views;
- Einstein/aperiodic tiling visualization;
- complex-base / omega / imaginary-base fractal coordinate visualization;
- mesh/vector/scalar overlays.

A view must carry a clear distinction between “visual transform” and “scientific transform.”

### Batch GWEB-5 — local AI / Research Notebook presentation

Add browser surfaces for:

- local AI on/off;
- provider selection/configuration with no-code setup;
- Research Idea objects;
- Keep / Useful / Reject;
- Minimal / Balanced / Exploratory graph proposals;
- Build on Canvas preview/approval;
- heartbeat visualization.

AI suggestions remain advisory and cannot promote verification.

## 8. API extensions: when needed

If Gemini reaches a feature that cannot be implemented without duplicating semantics, stop and add a typed backend endpoint.

Examples:

- graph-level validation;
- canonical module parameter validation;
- coordinate transform that changes scientific data;
- proof dependency queries;
- evidence/certificate verification;
- source-to-formal bridge status;
- long-running server-side jobs.

Backend extensions should be small, typed, tested and fail closed.

## 9. AI Studio preview rule

AI Studio's preview environment is useful for presentation development. A green AI Studio preview is **not** CACE qualification.

The final CACE application still requires the appropriate backend/native/formal gates:

- Python/API tests;
- native C++ build/tests;
- integration tests;
- security/provenance tests as applicable;
- Lean preflight/qualification only when proof-sensitive source is touched.

## 10. Current live-work separation

At handoff creation, active proof/runtime work exists outside the web integration branch:

- PR #42: v3.41A proof branch.
- PR #60: exact C++ P1/RT0/FSL runtime branch.

Keep Gemini web changes in their own branch/PR until those concerns can be deliberately integrated.

## 11. First prompt to give Google AI Studio

Use this as the initial implementation instruction after importing the repository:

> Read `GEMINI.md`, `CACE_AI_BUILDER_CONTRACT.md`, `CACE_AGENT_BOOTSTRAP.json`, and `docs/GEMINI_AI_STUDIO_HANDOFF.md`. Build the CACE browser presentation layer in React/TypeScript against the existing FastAPI endpoints in `api/index.py`. Do not duplicate scientific, graph-execution, exact-math, certificate, claim/proof, or Lean semantics in JavaScript/TypeScript/Node. Use a typed API client. Preserve the existing `web/` implementation until feature parity is tested. Start with GWEB-1 only and report changed files, tests, semantic impact, and whether any qualification-sensitive source changed.

## 12. Definition of success

The Gemini integration is successful when:

- a browser-only developer can understand the API contract without private chat context;
- Gemini knows exactly what code it may own;
- no browser implementation can manufacture scientific/proof success;
- the web UI can be replaced or evolved without forking CACE's scientific semantics;
- C++ and Lean remain independently testable and authoritative;
- proof work and browser work can proceed concurrently on isolated branches.
