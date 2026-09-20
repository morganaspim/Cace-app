# ADR-001 — Gemini + Base44 + Oracle/CACE Product Architecture

Status: **Accepted**

Date: 2026-09-20

This ADR is implementation/product architecture. It is not scientific evidence, proof qualification, or production-readiness evidence.

## Decision

CACE uses the following product split:

> **Gemini AI Studio Build Mode / Antigravity builds the interface. Base44 supplies low-volume commodity application services. Oracle/CACE remains the scientific authority and high-frequency data plane.**

The split is intentionally asymmetric. Neither Gemini nor Base44 may become an alternate scientific runtime, verifier, proof system, or evidence authority.

## Layer ownership

### Gemini AI Studio Build Mode / Antigravity

Gemini owns browser/product implementation:

- React/TypeScript presentation;
- drag/drop scientific canvas;
- 2D/3D visualization;
- coordinate/tiling/fractal presentation views;
- Research Assistant and Research Notebook presentation;
- run/proof/security dashboards;
- approval/recovery inbox UI;
- typed API clients;
- accessibility/responsive behavior;
- Help/examples;
- browser tests.

Gemini must consume CACE typed contracts rather than reimplement scientific semantics.

### Base44

Base44 is a **scarce, low-volume commodity-service layer**.

Allowed responsibilities:

- account/profile metadata;
- authentication/user-management integration where selected;
- workspace membership and collaboration metadata;
- lightweight notes/tags/preferences;
- ordinary app-level notifications when explicitly budgeted;
- low-frequency app metadata persistence.

Base44 is **not** the CACE event bus, scientific data plane, AI inference plane, proof store, high-frequency persistence layer, or telemetry pipeline.

The following must not be routed through Base44 merely for convenience:

- canvas drag/move events;
- scientific graph execution;
- run polling/streaming;
- worker telemetry;
- proof/verification polling;
- scientific artifacts;
- autonomous-agent turn traffic;
- model inference;
- raw scientific datasets;
- native-kernel results;
- proof-ledger events.

Those remain on Oracle/CACE or local/browser state according to the relevant contract.

### Oracle/CACE

Oracle/CACE owns all authoritative scientific and rigorous state:

- canonical Experiment/GraphExecutor semantics;
- module/type/unit validation;
- Python orchestration;
- C++ scientific/exact kernels;
- Lean formal source and qualification;
- verification records;
- certificates;
- canonical semantic/full hashes;
- proof/claim governance;
- local/autonomous scientific agent runtime;
- worker sandbox;
- cgroup/resource control;
- run artifacts;
- worker receipts;
- sandbox capability reports;
- scientific logs/provenance.

Only CACE may create authoritative scientific/verification/proof states.

## Authority rule

The frontend or commodity-service layer may **display** or **store references to** authoritative CACE state.

They may not synthesize:

- PASS;
- VERIFIED;
- FORMAL;
- theorem qualification;
- certificate validity;
- proof promotion;
- canonical experiment hashes;
- scientific correctness.

If a browser feature needs one of those values, it must call CACE.

## High-frequency rule

High-frequency state stays out of Base44.

Preferred paths:

```text
browser transient UI state
    -> local React state / IndexedDB where appropriate

scientific state
    -> CACE typed API
    -> Oracle CACE runtime/storage

low-volume account/app metadata
    -> Base44
```

## Free-tier-first constraint

CACE should remain usable on the selected free tiers.

The implementation must therefore:

1. keep Base44 metered actions below the monthly safety thresholds in `ops/base44_free_tier_budget.json`;
2. keep Oracle process/resource defaults within `ops/oracle_always_free_budget.json`;
3. avoid architectural dependencies that require a paid tier for correctness;
4. fail visibly when a free-tier resource is exhausted;
5. degrade optional convenience features before scientific correctness/security controls.

## Failure preference

When a commodity service is unavailable or over budget:

- CACE science must continue where safe;
- local/browser metadata may queue for later;
- proof/verification authority must not move to a lower-trust layer;
- paid fallback must never be silently enabled.

## Rationale

This split minimizes cost while preserving the strongest CACE invariant: scientific truth and proof authority remain inside the typed CACE core.

It also lets Gemini iterate rapidly on presentation and Base44 provide ordinary app services without coupling either platform to the scientific trusted-computing base.

## Consequences

Positive:

- low recurring cost;
- replaceable frontend;
- replaceable commodity backend;
- no scientific lock-in to Gemini/Base44;
- clear TCB;
- easier security review;
- free-tier budgeting is explicit.

Tradeoffs:

- more explicit API boundaries;
- some state exists in separate systems;
- offline/retry behavior must be designed for Base44 metadata writes;
- Oracle free-tier resource ceilings constrain concurrency.

## Related documents

- `GEMINI.md`
- `docs/GEMINI_AI_STUDIO_HANDOFF.md`
- `docs/GEMINI_IMPLEMENTATION_CONTRACT.md`
- `docs/BASE44_CREDIT_POLICY.md`
- `docs/ORACLE_ALWAYS_FREE_RESOURCE_POLICY.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY_ARCHITECTURE.md`


## Proof-contribution pathway

The layer split also applies to proof submissions:

```text
CACE UI
  -> optional Gemini packaging/draft formalization
  -> controlled GitHub draft PR
  -> CACE/Lean rigor pipeline
  -> operator PR review (ChatGPT-assisted if desired)
  -> canonical merge/qualification
```

For Enterprise proof-package requests, this same path happens before the proof is eligible for sale. Base44 may hold low-volume submission/order metadata, but it never stores authoritative proof truth or promotes evidence.

See `docs/PROOF_SUBMISSION_REVIEW_WORKFLOW.md`.


## Account entitlement boundary

Base44 owns/mirrors low-volume account entitlement metadata according to `ops/base44_account_tiers.json`.

This may control presentation such as:

- trial/access indicators;
- GPU/CUDA control visibility;
- Basic multithread unlock state;
- Researcher/Enterprise multithread inclusion;
- Enterprise commercial-use UI;
- Enterprise Full-Rigor Proof Package request eligibility.

It does not grant Base44 scientific/proof authority. CACE revalidates sensitive operations at the Oracle/CACE boundary.
