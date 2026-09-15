# CACE Studio Roadmap

This roadmap is dependency-ordered. Version labels are planning milestones, not evidence that a milestone is complete. Promotion requires its stated qualification evidence.

## v3.31 — Truth and formal qualification

Establish canonical claim/proof governance, fail-closed formal promotion, qualification-drift detection, exact-commit formal attestation, Python/native regression qualification and explicit separation of historical evidence from current evidence.

Exit condition: corrected qualification-sensitive source passes the pinned v3.30 Lean build, kernel axiom audit and full Python/native/package regression; the resulting content-addressed attestation is recorded in the canonical claim registry/proof ledger without qualification-sensitive drift.

## v3.32 — Repository and version normalization

Create one current repository narrative and machine-readable navigation for humans and AI agents. Keep historical milestone diaries separate from the current README. Add architecture/status/roadmap documents, generated source/module/claim indexes and a single canonical application/release version policy.

Exit condition: a new contributor or AI agent can determine architecture, current status, evidence boundaries, canonical version and qualification commands without reading historical release prose.

## v3.33 — Studio UX production pass

Harden the existing node editor rather than rebuild it: undo/redo, multi-select, copy/paste, alignment, zoom/minimap, search/filter, groups/subgraphs, typed validation, units, run-selected/subgraph, pause/cancel, deterministic execution controls, autosave and recovery.

## v3.34 — No-code local AI providers

Add a stable optional `AIProvider` layer with GUI discovery/configuration and health/model checks. Initial targets: Ollama and generic OpenAI-compatible local endpoints, including LM Studio/llama.cpp style servers. Modes remain OFF/Hints/Teacher/Researcher/Autonomous. AI cannot create evidence or promote proof status.

## v3.35 — Module and plugin SDK

Stabilize typed module contracts, plugin manifests, compatibility/versioning, scaffolding, trust levels and independent test requirements. Reduce version-specific wrapper debt without deleting historical evidence.

## v3.36 — Experiment and reproducibility v2

Version the `.cace` schema independently from the application. Add canonical serialization, deterministic fingerprints, content-addressed data, replay/drift reports and suitable large-data stores such as HDF5/Zarr/Arrow/Parquet where justified.

## v3.37 — Certified FEM/PDE end-to-end

Connect mesh validation, finite-element spaces, sparse assembly, solver, residual, a-posteriori estimator, interval/error bounds, adaptive refinement, certificate generation, proof trace and visualization. Preserve explicit assumptions for Lax–Milgram, Céa, Bramble–Hilbert, Aubin–Nitsche, equilibrated flux, reliability/efficiency, adaptivity, conditioning, DMP, FEEC, spectral and Prager–Synge results.

## v3.38 — Geometry/GA and legacy migration

Audit the historical 0–50 feature catalogue. Migrate real capabilities into typed modules/examples, classify maturity honestly, deprecate unsupported placeholders and strengthen the generic sparse Clifford/PGA/CGA foundation. Do not imply that demonstrations are production scientific solvers.

## v3.39 — Advanced research modules

Continue certified multiscale shear tiles, tail-certified Hilbert coordinates, complex product mosaics, adaptive dimension selection and coupled curved shear cells with explicit distortion, convergence/tail and performance evidence. Maintain Navier–Stokes, quantum/QAOA/boson and other difficult-science modules as rigorously scoped research tools, never as unsupported open-problem claims.

## v3.40 — Production engineering candidate

Cross-platform clean installs, native packaging, dependency locks, upgrade tests, security/trust review, fuzz/fault injection, performance/resource budgets, crash recovery, documentation qualification and release governance.

## Later phase — Immutable scientific provenance and distributed attestation

Build the approved provenance architecture:

`scientific artifact -> content address -> deterministic Merkle bundle -> signed verifier attestations -> append-only CACE transparency ledger -> optional external immutable timestamp/blockchain anchor`.

This layer strengthens tamper evidence, authorship/verification provenance and independent reproduction. It does **not** prove mathematics. CACE must work fully without a blockchain, token, cryptocurrency or network connection. External anchoring should use established infrastructure rather than a custom CACE cryptocurrency.

A future E5 `CROSS-VERIFIED` status may require independent verifiers to reproduce the same claim/source/dependency/artifact identity and sign artifact-bound attestations. CACE itself must not pretend to establish social/organizational independence merely from multiple keys; verifier identity and independence are separate trust questions.

## v4.0 — Production release

A v4.0 designation requires the production definition of done: current claims are traceable and appropriately qualified; experiments are reproducible; GUI/headless workflows are reliable; supported platforms/packages pass; security and provenance boundaries are documented; plugins and local AI are optional and stable; scientific modules advertise only evidence actually earned by their tested/formal scope.
