# CACE Build and Trust Guide

Status: primary architecture handoff for humans and repository-reading agents.

Use this guide to understand **what CACE is supposed to become, how to build it, what is trusted, what proves what, how defects are prevented from recurring, and where authoritative information lives**.

This guide is navigation and architecture. It is not verification evidence.

## 1. Start here

Read in this order:

1. `CACE_AGENT_BOOTSTRAP.json` — machine-readable single-entry navigation.
2. `docs/STATUS.md` — current implementation/qualification snapshot.
3. `docs/MASTER_BUILD_SPEC.md` — complete durable product goals.
4. `docs/GOAL_REGISTRY.json` — machine-readable goal list.
5. `docs/ARCHITECTURE.md` — runtime subsystem boundaries.
6. `docs/SECURITY_ARCHITECTURE.md` — security zones and threat boundaries.
7. `docs/CONSTITUTION.md` — non-negotiable scientific rules.
8. `docs/CLAIMS.md` — formal claim promotion and proof ledger rules.
9. `docs/BUG_FLUSH_ARCHITECTURE.md` — defect-to-permanent-guard process.
10. `docs/PROVENANCE_ATTESTATION.md` — evidence identity and independent preservation.
11. `docs/PRODUCTION_READINESS.md` — production dimensions and remaining gates.
12. `docs/AI_QUICKSTART.md` — headless machine interfaces.

## 2. Product architecture in one view

```
Browser / Desktop / CLI / Agent
              |
              v
      typed experiment graph
              |
              v
      canonical Python core
       /               \
      v                 v
C++ heavy kernels   verification/certificates
      |                 |
      +--------+--------+
               |
               v
        run/evidence record

Formal path is separate:

Lean source
   |
pinned Lean + Mathlib
   |
audited root compile
   |
Lean.Environment metadata
   |
kernel axiom audit
   |
exact-head attestation
   |
claim/proof promotion gate
```

All interfaces consume the same core semantics. The web UI must not invent a separate scientific truth model.

## 3. What proves what

### Formal theorem proof

Authority:

- Lean source;
- pinned Lean + Mathlib;
- kernel;
- axiom audit;
- exact endpoint metadata;
- exact-head artifact.

Does **not** prove:

- Python/C++ application correctness;
- web security;
- numerical conditioning;
- production readiness.

### Numerical validation

Authority:

- executable scientific code;
- numerical verifier;
- test data;
- tolerances/intervals/certificates as applicable.

Does **not** prove arbitrary continuum mathematics.

### Provenance

Authority:

- hashes;
- manifests;
- signatures;
- append-only ledger;
- independent mirrors.

Proves identity/history/tamper evidence only, not mathematical truth.

### AI output

Advisory only. Never evidence.

## 4. Proof rigor architecture

The formal pipeline is fail closed.

Required sequence:

1. exact source commit;
2. frozen proof plan and root-import policy;
3. unfinished-token rejection;
4. pinned dependency closure;
5. targeted/reverse-dependent compilation;
6. audited root compilation;
7. loaded-environment theorem metadata;
8. kernel axiom audit;
9. exact proof-contract endpoint equality;
10. executable/source binding;
11. content-addressed attestation;
12. independent artifact verification;
13. provenance promotion;
14. drift check for later descendants.

New theorem modules should normally follow:

`quarantine -> standalone Exact-Pin -> audited promotion -> audited-root Exact-Pin -> canonical qualification -> provenance overlay`

Never weaken theorem statements, axiom policy, negative tests, or guardrails merely to make CI pass.

## 5. Bug-flush architecture

A bug is not finished when one line is repaired.

For every confirmed defect:

1. reproduce;
2. classify the failure pattern;
3. fix the root cause;
4. sweep siblings/repository;
5. add regression test;
6. add permanent machine-detectable guard when possible;
7. aggregate independent checks in one validation cycle;
8. preserve diagnostics;
9. verify qualification drift separately.

Canonical implementation:

- `scripts/check_bug_sweep.py`
- `quality/bug_patterns.json`
- regression/property/adversarial tests
- native compile/smoke/sanitizer layers
- qualification-drift checks

Goal: **do not make the same class of mistake twice**.

## 6. Security architecture

Security authority is described in `docs/SECURITY_ARCHITECTURE.md`.

Key rules:

- browser/client state is untrusted;
- AI and plugins are outside the trusted evidence path;
- proof runner is isolated from untrusted web requests;
- no secrets in source/frontend;
- typed validation and least privilege at boundaries;
- long scientific/proof jobs run through controlled workers;
- zero-contact local AI has no network/cloud credentials/direct shell;
- critical evidence is stored outside GitHub as well.

## 6.1 Offline core, collaboration, and licensing

CACE's scientific worker is a zero-egress sandbox. Collaboration and licensing are separate network brokers with fixed capability protocols.

- Collaboration: invite-only shared canvas, viewer/editor roles, encrypted typed operations, no code/plugin/file injection.
- Licensing: day/week/month/year passes, Monero QR, external payment verification, signed offline license token.
- Payment/commercial state never alters mathematical evidence.
- Local app entitlement and project-funded remote compute are separate resources.

See `docs/OFFLINE_COLLABORATION_AND_LICENSING.md`.

## 7. Provider-independent evidence retention

GitHub logs are not the source of truth.

Critical runs should preserve:

- stdout/stderr;
- step/command exit codes;
- exact source commit;
- toolchain/dependency identities;
- generated artifacts;
- per-file hashes;
- canonical manifest hash;
- PASS/FAIL/NOT_RUN state.

Preferred copies:

1. durable runner filesystem;
2. persistent system journal;
3. OCI Object Storage;
4. optional independent secondary mirror;
5. GitHub as an additional convenience copy.

## 8. Webapp construction requirements

The target is a real browser scientific Studio, not a static demo.

Required major surfaces:

- module library;
- drag/drop graph canvas;
- typed click-to-connect ports;
- parameters and validation;
- run controls and heartbeats;
- proof/evidence explorer;
- Research Idea notebook;
- proposed experiment preview/build;
- coordinate/tiled visualization modes;
- interactive 2D/3D mode;
- save/load/replay/export/print;
- optional local AI provider setup;
- explicit failure and evidence state.

The web app should use canonical server/core contracts rather than duplicate scientific logic in JavaScript.

## 9. Presentation versus semantics

Examples of presentation-only state:

- pan/zoom;
- 3D camera orientation;
- coordinate grid style;
- square/hex/fractal visual tiling;
- lighting;
- UI panel layout.

These do not alter the semantic experiment hash or proof status.

If a basis transform, snapping operation, quantization, coordinate conversion, geometry mutation, or projection changes computation, it must be represented as an explicit typed graph operation and dependent evidence must be recomputed.

## 10. Local AI architecture

AI is optional.

Target capabilities:

- explain modules/proofs/results;
- suggest experiments;
- propose graphs;
- help navigate rigor;
- create Research Ideas;
- assist with demos.

Target strongest isolation:

- no Internet;
- no cloud credentials;
- no arbitrary shell;
- no arbitrary host filesystem;
- bounded capability broker;
- audit log;
- human approval for consequential mutation.

## 11. Build/implementation discipline

Before calling a feature complete, require:

- stable entry point/module;
- typed contract;
- assumptions and limitations;
- tests;
- evidence class;
- serialization/reproducibility behavior;
- UI/API wiring where required;
- failure behavior;
- security implications;
- documentation;
- acceptance criteria from the goal registry.

## 12. Release/production discipline

A release candidate needs separate evidence for:

- theorem qualification;
- Python/native regression;
- web behavior;
- package/install behavior;
- security;
- reproducibility/provenance;
- performance/resource budgets;
- deployment/health/recovery.

No one dimension substitutes for another.

## 13. Repository truth hierarchy

When sources disagree, prefer:

1. exact source at the checked-out commit;
2. canonical claim/proof data for promoted formal claims;
3. exact run artifacts/attestations;
4. Constitution/Claims/Architecture/Security policy;
5. current Status;
6. Master Build Spec and Goal Registry;
7. historical notes.

## 14. Agent handoff rule

An agent that can read only a repository snapshot should still be able to determine:

- what to build;
- what is already implemented;
- what is formally qualified;
- what remains research;
- how to run tests;
- how to preserve evidence;
- how to handle bugs;
- what security boundaries may not be crossed.

If that is not possible from the repository alone, repository discoverability is incomplete.
