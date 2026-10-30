# CACE Current Implementation Program A–I

Status: current implementation organization for coding agents. It consolidates durable CACE goals; it does not claim these items are complete.

This document is intentionally compact enough for Gemini AI Code Studio and Antigravity to load before source code. Detailed acceptance criteria live in `docs/MASTER_BUILD_SPEC.md` and `docs/GOAL_REGISTRY.json`; every preserved research/product idea remains in `docs/CHAT_IDEA_LEDGER.md`.

## Global ordering rule

Current near-term dependency order remains:

`Rigorous Math Kernel v1 -> Proof-backed Math Toolbox -> composable Science Modules -> Help/Examples -> major Gemini browser polish`.

Formal/source-to-formal work continues only through the fail-closed proof architecture and must not be weakened by UI/AI work.

---

## A — Proof, evidence, and regression truth baseline

Gemini/Antigravity may also create new C++ rigorous tools, exact checkers, Lean proofs and source-to-formal bridges under `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`. If a proof cannot be finished, preserve the contribution as a validated proof-ready C++/Lean tool submission packet rather than abandoning the work.


Purpose: make CACE incapable of overstating mathematical/scientific status.

Includes:
- exact-current-head Lean qualification;
- claim registry / proof ledger;
- source-to-formal runtime binding;
- evidence classes and NOT_RUN/stale/fail-closed behavior;
- proof dependency explorer;
- reproducibility/provenance separation from proof;
- regression/fault-injection/bug-flush guardrails;
- exact/certified runtime objects and RMK foundations.

Current important work:
- RMK-v1;
- runtime packet/source-to-formal linkage;
- discrete -> H1/H(div) -> volumePairing -> continuum bridges only when explicitly proved/qualified.

Never infer FORMAL from a Lean filename, model output, numerical success, heartbeat, or provenance hash.

## B — Build Lite, reliability, testing, and low-cost qualification

Purpose: make development fast without weakening rigor.

Includes:
- local-first targeted tests/builds;
- dependency-aware Build Lite selection;
- one-expensive-proof-job-at-a-time;
- safe Lean/toolchain caches;
- batched Exact-Pin preflight;
- deterministic source indexes;
- fault-family sweeps after bugs;
- performance/resource observability;
- CI only when it provides independent clean-environment value.

Goal: coding agents should test as much as possible before asking the user to launch an expensive runner job.

## C — Hardened production service, accounts, deployment, and security

Purpose: make the browser-accessible product deployable without exposing scientific/proof authority.

Includes:
- API/session/service hardening;
- Oracle/production hosting;
- authentication/account tiers where retained by current product policy;
- security boundaries and least privilege;
- proof runner isolation from untrusted requests;
- source secrecy / release classification;
- durable logs independent of GitHub;
- save/export/replay;
- controlled long-job workers;
- packaging/installers and recovery.

The web/service layer may orchestrate canonical CACE semantics but may not author scientific truth.

## D — Scientific UX and browser Studio

Purpose: deliver the full no-code scientific playground.

Includes:
- module library;
- drag/drop;
- typed click-to-connect;
- parameter/property forms;
- validation;
- groups/subgraphs/macros;
- undo/redo;
- autosave/crash recovery;
- results/data/plot/performance/provenance docks;
- Proof Explorer;
- 2D/3D interaction;
- visualization-only coordinate systems: Cartesian, triangular, hexagonal, Einstein/aperiodic, complex-base/i/omega, hierarchical/fractal;
- Help pages and runnable examples;
- browser presentation built by Gemini against the typed CACE API/core.

Hard boundary: JS/TS/Node presentation must not duplicate scientific, exact-math, proof, claim, or qualification semantics.

## E — Research Notebook and experiment synthesis

Purpose: turn discoveries into durable, executable research objects.

Includes:
- Research Idea object;
- fields: title, notes, hypotheses, proposed experiment, associated modules, evidence/provenance;
- lifecycle: Idea -> Testable -> Experimented -> Promising -> Proof Candidate;
- Keep / Useful / Reject;
- Proposed Experiment -> preview -> Build on Canvas;
- Minimal / Balanced / Exploratory proposal strategies;
- editable research logs and report export;
- AI-drafted discussion clearly marked as generated;
- no workflow status implies truth/proof.

## F — Sandboxed Local AI / CACE-owned agent runtime

The Local AI should be able to propose and build reusable CACE tools through the same rigorous contribution pipeline, subject to capability/approval policy. Accepted tools become additional typed capabilities available to later experiments.


Purpose: create CACE's own provider-independent agentic AI.

Includes:
- Local / Zero Contact, Hybrid, and General Agent modes;
- provider-neutral AgentController / ModelProvider;
- local LLM + optional cheap neural/ranking/math components;
- typed capability-scoped CACE Tool Bus;
- bounded planning/action/observation loop;
- resource/tool/token budgets;
- checkpoint/recovery;
- optional Gemini/other adapters;
- later specialist roles: Math, Proof, FEM, Physics, Experiment, Critic, Librarian;
- AI OFF remains fully functional.

Google Antigravity and Gemini are preferred builders/orchestration surfaces, not proof authorities and not mandatory runtime dependencies.

### M.E.R.L.I.N. source-access v25 implementation order

1. Confirm selected v25 tests and bug sweep in exact-commit CI; a prior green commit is not enough.
2. Integrate real CACE authenticated principal/session rights with the host resolver and cross-tenant row/field policy.
3. Add enforceable low-privilege no-egress OS worker sandbox, bounded CPU/memory and secret isolation. The v25 spawn/HMAC prototype is not a sandbox.
4. Independently test query differencing, group-count leakage, token replay, revocation and malicious-model routes.
5. Add typed source observations to canonical Research Notebook and specialist council without permitting AI proof promotion.
6. Complete full Python/native/qualification-drift and pinned Lean gates through the approved release process.


## G — Heartbeat, Grow, coordination, and distributed research

Heartbeat includes a typed Agent Perception Packet carrying compact live node-state, residual/convergence, blocker, resource and canonical-evidence deltas. This is the agent's non-evidentiary sensory stream for following the experiment as the canvas evolves.


Purpose: make long research tasks observable, resumable, and cheap to coordinate.

Includes:
- Conway-inspired semantic canvas heartbeat field;
- deterministic states such as dormant/ready/active/waiting/blocked/stale/verifying/verified/failed/research-interest;
- separate agent liveness/progress/checkpoint heartbeats;
- leases and stall/loop detection;
- heartbeat deltas to focus AI attention without rereading the full canvas;
- Grow seeded random walks and combinatorial/group constructions;
- spare-compute scheduling research;
- deterministic task addressing research where useful;
- later distributed workers/collaboration only after single-machine contracts stabilize.

Heartbeat/activity can mirror canonical verification but can never create it.

## H — Molecular, protein, materials, and broader science expansion

Purpose: make the science canvas full-featured and cross-domain.

Includes:
- typed atoms/bonds/molecules;
- safe low-risk educational chemistry mode;
- protein structure import with provenance/license metadata;
- low-cost deterministic/coarse fold-search research with honest limitations;
- materials candidate screening with explicit heuristic/surrogate/physics/database/measured evidence;
- particle/field/theoretical-physics canvas objects with established vs theoretical labels;
- statistics/data/signals/optimization/quantum modules;
- shared typed geometry/mesh/field/material/solution/evidence objects;
- every production module: units, assumptions, verification, reproducibility, Help, examples.

## I — Certified PDE/FEM and rigorous math/science expansion

Purpose: make CACE's flagship rigorous science chain deep and reusable.

Canonical pipeline:
`Geometry -> Mesh -> FE space -> Assembly -> Solver -> Residual -> Estimator -> Interval/Certificate -> Adaptive Refinement -> Evidence/Proof Trace -> Visualization`.

Includes:
- arbitrary mesh / P1 / RT0 / higher-order paths;
- equilibrated flux;
- Prager-Synge/hypercircle;
- estimator reliability/efficiency;
- Stokes / Maxwell / parabolic / nonlinear / DG-SUPG / elasticity/contact/Helmholtz families as contracts mature;
- sparse verified eigenvalue tools;
- exact/symbolic/interval oracles for reference problems;
- explicit theorem applicability;
- production scientific Help/examples;
- proof-backed mathematical toolbox supporting algebra, linear algebra, calculus, geometry, exterior/graded algebra, combinatorics, analysis, variational/FEM, transforms, optimization, and certified numerical tools.

---

## Cross-cutting idea preservation

The A–I plan is an execution map, **not a filter that deletes ideas**.

All durable accepted goals remain in `docs/GOAL_REGISTRY.json`.
All meritorious deferred/research ideas remain in `docs/CHAT_IDEA_LEDGER.md`.

Builders must consult both before declaring a track complete.

## Completion behavior

A track is not "done" because code exists. It requires the acceptance criteria associated with its goals, tests, documentation, security/evidence boundaries, and any applicable formal qualification.

After finishing a batch, update repository-visible plan/status/goal records so the next AI session can continue without chat history.
