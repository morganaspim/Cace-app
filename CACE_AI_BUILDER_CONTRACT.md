# CACE AI Builder Contract

Status: authoritative implementation-governance specification for AI code builders. It is **not** scientific evidence, proof evidence, qualification evidence, or production-readiness evidence.

Primary implementation environment: **Gemini AI Code Studio**. Other coding agents may be used, but every agent is bound by the same contract.

## 1. Purpose

This contract lets an AI builder implement CACE quickly without being allowed to redefine mathematical truth, evidence semantics, qualification state, or the trusted computing base.

The core rule is:

> AI may build software around CACE's scientific and formal interfaces, but it may not decide that an unresolved mathematical or verification obligation is satisfied.

CACE must remain usable with AI disabled.

## 2. Authority order

Before changing scientific, proof, evidence, security, or execution behavior, read and obey:

1. `CACE_AGENT_BOOTSTRAP.json`
2. `AGENTS.md`
3. `docs/CROSS_CHAT_HANDOFF.md`
4. `docs/BUILD_AND_TRUST_GUIDE.md`
5. `docs/STATUS.md`
6. `docs/ARCHITECTURE.md`
7. `docs/CONSTITUTION.md`
8. `docs/CLAIMS.md`
9. `docs/BUG_FLUSH_ARCHITECTURE.md`
10. `docs/PROVENANCE_ATTESTATION.md`
11. `docs/MASTER_BUILD_SPEC.md`
12. `docs/GOAL_REGISTRY.json`
13. `AI_REPO_MAP.json`
14. the relevant proof/feature roadmap
15. `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md` when runtime/formal linkage is touched

When these documents disagree with exact checked-out source, exact source wins for current behavior. Claim/proof promotion still follows the canonical claim registry, proof ledger, formal source, and exact qualification artifacts.

## 3. Trust boundary

### AI is advisory and untrusted

AI-generated code, text, tests, theorem sketches, inferred mappings, or explanations are never verification evidence.

An AI builder may:

- implement typed application/UI/runtime code;
- add tests and guardrails;
- refactor while preserving contracts;
- propose Lean statements/proofs;
- add quarantined proof modules;
- generate documentation and implementation plans;
- wire existing qualified theorem endpoints into fail-closed runtime consumers.

An AI builder may **not**:

- set or imply formal PASS because code/tests look correct;
- replace a theorem obligation with `axiom`, `sorry`, caller assertions, or unchecked metadata;
- weaken negative tests, qualification checks, theorem statements, or evidence gates to obtain green CI;
- map `NOT_RUN`, missing evidence, stale evidence, or unavailable verification to PASS;
- treat numerical agreement as continuum proof;
- treat source provenance, signatures, hashes, or logs as mathematical proof;
- silently change scientific semantics in presentation/UI code;
- claim that a runtime object satisfies Lean hypotheses unless an explicit source-to-formal bridge establishes that binding.

## 4. Stable architecture the builder must preserve

The preferred dependency direction is:

`GUI/web/agents -> typed API/core -> scientific modules -> exact/certified runtime -> formal bridge -> canonical proof gate`

Do not invert this dependency. GUI code must not create alternate scientific semantics. AI-specific code must remain outside the evidence trusted-computing base.

Python orchestrates. **C++ is the default home for production scientific and mathematical runtime kernels**, including mesh geometry, exact arithmetic, finite-element algebra/assembly, solvers, estimators, and other load-bearing computations. Lean remains the formal proof source.

Python may provide GUI/API orchestration, module graph execution, serialization/provenance, configuration, thin native bindings, and independent reference/checker implementations. A Python reference implementation must not silently become a second canonical scientific truth path when an equivalent C++ production kernel exists. New load-bearing scientific semantics should therefore be implemented in C++ first unless a written design note justifies another placement.

## 5. Change classes

Every proposed change must be classified before implementation.

### Class A — presentation only

Examples: layout, camera, pan/zoom, coordinate-grid appearance, visual tiling, help text.

Requirements:
- no change to scientific result identity;
- no promotion of evidence;
- existing semantic hashes remain valid unless actual semantic state changed.

### Class B — ordinary software semantics

Examples: typed graph editing, persistence, module registry UX, non-proof API changes.

Requirements:
- typed contract;
- validation;
- unit/regression tests;
- stale-evidence invalidation where relevant;
- reproducible serialization.

### Class C — scientific/runtime semantics

Examples: new numerical method, FE representation, solver, estimator, certificate, coordinate transform that changes computation.

Requirements:
- explicit assumptions;
- units/types;
- failure modes;
- evidence class;
- meaningful numerical/exact/certified tests;
- no formal claim beyond an existing bridge.

### Class D — runtime/formal linkage

Examples: binding a runtime mesh, P1 field, RT0 field, graph-space datum, or certificate to a Lean theorem hypothesis.

Requirements:
- follow `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md`;
- exact representation identity or a proved abstraction relation;
- explicit unresolved hypotheses;
- fail-closed bridge certificate;
- proof-contract identity;
- canonical qualification anchor;
- adversarial tests proving near/equivalent-looking but unbound data do not pass.

### Class E — formal proof / qualification-sensitive

Examples: `formal/**`, proof contracts, theorem metadata, axiom audits, qualification-sensitive formal bridge semantics.

Requirements:
- quarantine first;
- cheap/static checks first;
- Exact-Pin preflight;
- audited promotion;
- audited-root Exact-Pin;
- canonical exact-current-head qualification;
- provenance overlay only after qualification;
- never retry an unchanged failure blindly.

## 6. Module implementation contract

Every new or materially changed scientific module must provide:

- stable module ID and version;
- typed inputs/outputs;
- parameter validation;
- assumptions;
- evidence kind and maturity;
- deterministic/reproducible behavior where feasible;
- limitations/nonclaims;
- unit tests;
- regression tests;
- verification behavior that can emit PASS, FAIL, or NOT_RUN honestly;
- serialization/provenance fields needed to reproduce the run.

Version labels and module-local proof metadata are not proof evidence.

## 7. Proof-status lifecycle

Use these concepts separately:

1. **experimental** — exploratory behavior only;
2. **numerically validated** — tested numerical behavior within stated scope;
3. **exact/certified** — exact symbolic, interval, or checker-backed evidence within stated scope;
4. **formally connected** — a runtime representation has an explicit bridge to stated Lean hypotheses/endpoints;
5. **formally verified** — the relevant Lean theorem has passed canonical qualification for the exact source state;
6. **current-head qualified** — proof provenance is valid for the present source after drift checks.

Do not collapse these states into a single boolean.

The GUI may summarize them visually, but the canonical evidence state comes from core contracts, claim/proof data, and qualification artifacts.

## 8. Runtime-to-formal rule

A qualified theorem is not automatically a theorem about arbitrary Python/C++ runtime data.

For every runtime-to-Lean use, the builder must answer:

- What exact runtime object is being represented?
- What Lean object does it correspond to?
- Is the correspondence exact, generated, serialized, reconstructed, or conditional?
- Which hypotheses are already discharged?
- Which hypotheses remain unresolved?
- Which theorem establishes each discharge?
- Which proof contract and qualification anchor apply?
- What input perturbation would cause the bridge to fail?

If any answer is missing, the bridge remains NOT_RUN/unresolved.

## 9. Testing discipline

Before proposing a merge, run the cheapest relevant tests first.

Minimum expectations:

- direct unit tests for changed code;
- nearby regression tests;
- negative/adversarial tests for trust-boundary code;
- repository sibling sweep for repeated defect patterns;
- static/source sanity checks;
- aggregate tests appropriate to the change class.

For proof-sensitive work, passing Python tests does not replace Lean qualification.

Every defect class discovered should become a regression guard when practical.

## 10. CI and cost discipline

Prefer grouped work over many expensive runs.

- Build and test locally/cheaply first.
- Keep theorem work quarantined until coherent.
- Batch ready theorem targets when the existing batch preflight can do so without weakening rigor.
- Do not create multiple expensive runner jobs when one serialized batch will reveal the same failure frontier.
- Cache work, never truth.
- Keep canonical qualification separate from preflight.

## 11. Gemini implementation workflow

For each bounded implementation batch Gemini should:

1. read this contract and the relevant canonical docs;
2. state the exact files/interfaces it plans to touch;
3. classify each change A-E;
4. preserve all current nonclaims;
5. implement the smallest coherent batch;
6. run cheap tests and static checks;
7. add regression guards for discovered defect classes;
8. output a handoff containing:
   - changed files;
   - tests run/results;
   - unresolved obligations;
   - evidence/qualification impact;
   - whether any qualification-sensitive source changed;
   - recommended next gate.

Do not mix unrelated feature work into a proof-sensitive batch.

## 12. Formal-source protection rules

The builder must never:

- auto-edit canonical proof provenance solely to match expected tests;
- add a theorem to the public proof contract before its intended qualification path is ready;
- infer theorem dependency edges from prose when Lean.Environment metadata is the required authority;
- modify claim/ledger truth to paper over a stale or failed qualification;
- describe a quarantined or preflight-only theorem as canonically qualified.

## 13. Source-to-formal implementation target

The current high-value bridge program is defined in:

`docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md`

Its goal is to connect concrete runtime/finite-element objects to exact Lean objects and then, where mathematically justified, to the bounded-box H1/H(div)/Green-pairing continuum chain.

Until those bridges exist, preserve the explicit nonclaim that arbitrary runtime finite-element fields satisfy the continuum theorem hypotheses.

## 14. Definition of a successful AI-built change

An AI-built change is successful only when:

- the implementation satisfies its typed contract;
- relevant tests pass;
- failure states remain visible;
- evidence semantics are unchanged unless deliberately and correctly extended;
- proof-sensitive changes follow the full proof workflow;
- documentation matches exact behavior;
- unresolved obligations are preserved rather than hidden.

Fast code generation is useful. Trust is earned only through CACE's independent contracts and verification pipeline.
