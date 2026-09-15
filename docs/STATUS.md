# CACE Studio Current Status

Status date: 2026-09-14. Development branch: `implement/v331-truth-foundation`.

CACE is a research/development system. Production readiness is not established. Mathematical proof status, runtime verification, numerical evidence and software maturity are intentionally tracked separately.

## Current implementation focus

The v3.31 truth foundation adds a canonical claim registry, proof ledger, fail-closed formal-evidence gate and qualification-drift audit. Historical or module-local formal results do not automatically become current public formal evidence. A current qualification requires an exact attested source commit, content-addressed proof artifact, workflow provenance, explicit checks, no blockers and no later qualification-sensitive drift.

The development line also has a functioning PySide6 visual graph editor, module registry, graph executor, run certificates, headless CLI, native C++ runtime/tests, pinned Lean project and a broad research-module catalogue. These capabilities have different maturity and evidence levels and must not be summarized as a single blanket verification claim.

## Formal v3.30 qualification state

The v3.23-v3.30 continuum proof-strengthening claim is **not yet promoted in the canonical proof ledger**.

A diagnostic self-hosted v3.30 workflow established that runner allocation, pinned Python, TLS trust, Lean 4.32.1 installation, the pinned Mathlib commit, claim-promotion tests and unfinished-proof-token rejection execute successfully. That diagnostic build then exposed localized Lean source errors in `RegularizationClosure.lean` and `BoxClassicalAgreement.lean`; those errors were repaired on the v3.31 branch without weakening theorem statements.

A prior exact-head Python regression on the v3.31 branch passed native CMake/CTest and reported 508 passing Python tests with four failures. Three failures were legacy expectations that contradicted the new fail-closed formal-evidence policy, and one was a qualification-drift path-normalization bug. Those four issues were repaired on the current correction commit.

The authoritative next evidence is a fresh self-hosted Python regression plus v3.30 Lean build/kernel-axiom audit for the corrected qualification-sensitive commit. Until they pass and the attestation digest is accepted into the canonical ledger, v3.30 remains unqualified.

## Production blockers after v3.31 qualification

The next engineering priorities are repository/version normalization, production hardening of the visual scientific playground, no-code local-AI providers, a stable module/plugin SDK, reproducible experiment bundles, Proof Explorer, certified FEM/PDE end-to-end workflows, legacy-module audit/migration, packaging/security/compatibility qualification and performance budgets.

Open mathematical research obligations must remain explicit. In particular, conditional H1/H(div) bridge theorems do not become unconditional simply because surrounding infrastructure compiles. CACE must preserve theorem hypotheses and distinguish reductions/criteria from completed analytic constructions.

## Source of truth

For claims, use `cace_studio/data/claim_registry.json`, `cace_studio/data/proof_ledger.json` and `docs/CLAIMS.md`. For formal source, use `formal/cace_formal/`. For software behavior, use exact-commit test/run evidence. For project rules, use `docs/CONSTITUTION.md`. Historical release notes are context only and do not qualify the current source state.
