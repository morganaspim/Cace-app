# CACE Studio Roadmap

This roadmap is dependency-ordered. Version labels are planning milestones, not evidence that a milestone is complete. Implementation, regression qualification, formal qualification and production readiness are separate states.

## v3.31 — Truth and formal qualification

Establish canonical claim/proof governance, fail-closed formal promotion, qualification-drift detection, exact-commit formal attestation, Python/native regression qualification and explicit separation of historical evidence from current evidence.

Current state: implementation exists; qualification remains open because the latest exact-head self-hosted run terminated before Lean compilation. The canonical v3.30 continuum claim remains unqualified.

Exit condition: corrected qualification-sensitive source passes the pinned v3.30 Lean build, kernel axiom audit and full Python/native/package regression; the resulting content-addressed attestation is verified and recorded in the canonical claim registry/proof ledger without qualification-sensitive drift.

## v3.32 — Repository and version normalization

Create one current repository narrative and machine-readable navigation for humans and AI agents. Keep historical milestone diaries separate from the current README. Add architecture/status/roadmap documents, deterministic source/module/claim/proof indexes and a single canonical application/development version policy.

Current candidate state: documentation, AI navigation, deterministic index generator and development-version normalization to `3.36.0.dev1` are prepared. Generated indexes still need exact-head generation/freshness validation in the consolidated regression environment.

Exit condition: a new contributor or AI agent can determine architecture, current status, evidence boundaries, canonical version and qualification commands without reading historical release prose, and generated indexes match canonical source.

## v3.33 — Studio UX production pass

Harden the existing node editor rather than rebuild it: undo/redo, selection/deletion, copy/paste where supported, alignment/organization, zoom/search/filter, typed validation, deterministic execution controls, autosave/recovery and explicit invalidation of stale verification evidence after graph edits.

Current candidate state: a substantial first production pass is implemented. Full UX/platform qualification remains pending.

## v3.34 — No-code local AI providers

Add a stable optional `AIProvider` layer with GUI discovery/configuration and health/model checks. Initial targets include Ollama and compatible local endpoints. Modes remain OFF/Hints/Teacher/Researcher/Autonomous. AI cannot create evidence or promote proof status.

Current candidate state: local-provider infrastructure and GUI configuration are implemented with AI disabled by default and loopback-oriented security restrictions. Exact-head regression/platform qualification remains pending.

## v3.35 — Module and plugin SDK

Stabilize typed module contracts, plugin manifests, compatibility/versioning, scaffolding, trust levels and independent test requirements. Reduce version-specific wrapper debt without deleting historical evidence.

Current candidate state: versioned plugin manifests/SDK and fail-closed compatibility/trust validation are implemented. Broader third-party plugin compatibility and production security review remain later qualification work.

## v3.36 — Experiment, reproducibility and provenance v2

Version experiment/reproducibility structures independently from application marketing versions. Add canonical serialization, deterministic fingerprints, content-addressed evidence, replay/drift information, Proof Explorer, tamper-evident evidence bundles, signed attestations and conservative cross-verification policy.

Current candidate state includes:

- deterministic experiment/reproducibility fingerprints;
- content-addressed evidence artifacts/bundles;
- Evidence Ledger structures;
- Proof Explorer core and Studio integration;
- Ed25519 signed attestations using a vetted cryptographic library when the optional attestation dependency is installed;
- headless key-generation/sign/verify commands;
- fail-closed E5 evaluation requiring canonical current-head formal qualification before independent attestations can count;
- exact bundle/claim/commit/proof-artifact binding and distinct approved verifier identities/keys;
- explicit `proof_effect: none` semantics for provenance/signature operations.

E5 or signatures never create mathematical proof. They can only add independent provenance/cross-verification evidence to a claim that has already earned its underlying formal status.

Exit condition: consolidated candidate passes native/Python/package regression and required formal requalification, schemas/CLI round-trip correctly, and provenance failures remain fail-closed.

## v3.37 — Certified FEM/PDE end-to-end

**Start only after v3.31 is closed and the consolidated v3.32-v3.36 candidate has passed its regression/formal requalification wave.**

Connect mesh validation, finite-element spaces, sparse assembly, solver, residual, a-posteriori estimator, interval/error bounds, adaptive refinement, certificate generation, proof trace and visualization. Preserve explicit assumptions for Lax–Milgram, Céa, Bramble–Hilbert, Aubin–Nitsche, equilibrated flux, reliability/efficiency, adaptivity, conditioning, DMP, FEEC, spectral and Prager–Synge results.

Priority order inside v3.37:

1. canonical mesh/space/assembly contracts and exact topology validation;
2. sparse P1/RT0 numerical pipeline with deterministic fixtures;
3. residual/equilibrated-flux estimators and explicit assumption reporting;
4. interval/certified numerical bounds where mathematically justified;
5. adaptive refinement plus replayable certificates;
6. Proof Explorer links from numerical certificate obligations to exact/formal dependencies;
7. cross-backend validation and performance budgets without confusing backend agreement with proof.

## v3.38 — Geometry/GA and legacy migration

Audit the historical 0–50 feature catalogue. Migrate real capabilities into typed modules/examples, classify maturity honestly, deprecate unsupported placeholders and strengthen the generic sparse Clifford/PGA/CGA foundation. Do not imply demonstrations are production scientific solvers.

## v3.39 — Advanced research modules

Continue certified multiscale shear tiles, tail-certified Hilbert coordinates, complex product mosaics, adaptive dimension selection and coupled curved shear cells with explicit distortion, convergence/tail and performance evidence. Maintain Navier–Stokes, quantum/QAOA/boson and other difficult-science modules as rigorously scoped research tools, never as unsupported open-problem claims.

## v3.40 — Production engineering candidate

Cross-platform clean installs, native packaging, dependency locks, upgrade tests, security/trust review, fuzz/fault injection, performance/resource budgets, crash recovery, documentation qualification, release governance and reproducible-build/provenance operations.

## Later provenance hardening — distributed operations and optional external anchor

The core provenance architecture is now partly implemented in the v3.36 candidate. Later work should harden operations rather than invent a CACE blockchain:

`scientific artifact -> content address -> deterministic evidence bundle/Merkle root -> signed verifier attestations -> append-only CACE transparency/evidence ledger -> optional established external timestamp/blockchain anchor`

Remaining later-phase priorities:

1. production verifier key lifecycle, revocation and rotation policy;
2. explicit organizational identity/independence policy separate from key possession;
3. append-only transparency-log operation and audit/export format;
4. multi-machine reproduction workflows and reproducible environment manifests;
5. E5 governance rules for approved independent verifiers;
6. optional anchoring adapter to an established timestamp/transparency/blockchain system;
7. Proof Explorer visualization of provenance/attestation graphs and anchor status;
8. threat-model review covering stolen keys, compromised verifiers, dependency compromise and non-reproducible builds.

This layer strengthens tamper evidence, authorship/verification provenance and independent reproduction. It does **not** prove mathematics. CACE must work fully without blockchain connectivity, tokens or cryptocurrency. External anchoring should use established infrastructure rather than a custom CACE cryptocurrency.

## v4.0 — Production release

A v4.0 designation requires the production definition of done: current claims are traceable and appropriately qualified; experiments are reproducible; GUI/headless workflows are reliable; supported platforms/packages pass; security and provenance boundaries are documented; plugins and local AI are optional and stable; scientific modules advertise only evidence actually earned by their tested/formal scope.
