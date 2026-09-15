# CACE production-readiness assessment

Assessment date: 2026-09-14. Current development line: v3.31 truth/formal qualification. Overall status: **research/development; production readiness not established**.

Production readiness is intentionally stricter than mathematical proof status. A formally checked theorem does not imply the desktop application, native runtime, packaging, security model or every scientific module is production-qualified. Conversely, robust software tests do not prove continuum mathematics.

## Current highest-priority gate

The current blocker is exact-source qualification of the v3.31 truth foundation and v3.30 continuum proof-strengthening workflow.

The self-hosted Actions runner is operational. Diagnostic runs have successfully executed pinned Python setup, claim-promotion guard tests, isolated formal build setup, verified TLS, Lean 4.32.1 installation, pinned Mathlib resolution/cache and rejection of unfinished proof tokens. A diagnostic `lake build CACEFormal` then exposed localized source errors in `RegularizationClosure.lean` and `BoxClassicalAgreement.lean`; those compiler errors were repaired without weakening the affected theorem statements.

A prior exact-head Python/native regression successfully completed CMake and CTest and reached 508 passing Python tests with four failures. Three failures were legacy expectations that unregistered historical FORMAL records should count as current evidence; the new fail-closed policy correctly rejects that assumption. The fourth was a `.github` path-classification bug in qualification drift. All four were repaired on the current correction line.

A fresh corrected Python/native regression and pinned Lean build/kernel axiom audit are required before v3.30 can be promoted in the canonical proof ledger. Until that attestation is accepted, the current formal claim remains `NOT_RUN`/unqualified at the public claim-governance layer.

## Production qualification dimensions

### Correctness and claim integrity

Required: fail-closed verification, adversarial malformed-input tests, exact certificate replay, no unsupported evidence promotion, theorem hypotheses preserved, and claim/proof artifacts tied to source and dependencies.

Current direction: v3.31 adds the canonical claim registry, proof ledger, formal promotion gate and qualification-drift audit. This materially improves claim integrity but does not by itself make CACE production-ready.

### Reproducibility and provenance

Required: versioned `.cace` format, deterministic/canonical serialization where appropriate, content-addressed data/results, environment/dependency identities, replay and drift reports, and exportable verification evidence.

Later extension: signed Merkle research bundles, distributed reproducer attestations, an append-only transparency ledger and optional external timestamp/blockchain anchoring. See `docs/PROVENANCE_ATTESTATION.md`. This provenance layer must never substitute for mathematical verification.

### Cross-platform packaging

Required: clean supported-platform installs, native-library packaging, dependency locks, wheel/application qualification, upgrade/rollback tests and explicit support matrix. Current self-hosted ARM64 qualification is valuable but insufficient as the only platform evidence.

### GUI reliability

Required: hardened node editing, validation, undo/redo, recovery/autosave, deterministic execution controls, cancellation, clear failure states and integration tests for save/load/run/proof inspection. The existing GUI already provides drag/drop modules, click-to-connect typed ports, forms, execution and verification views; production work should harden rather than rebuild these capabilities.

### Plugin and local-AI boundaries

Required: versioned plugin SDK, capability/trust declarations, compatibility tests and sandbox/trust policy. Local AI must remain optional and outside the trusted evidence path. No-code provider discovery/configuration is planned after core truth/reproducibility contracts stabilize.

### Security

Required: artifact/schema validation, path/file safety, untrusted plugin boundaries, dependency integrity, signing-key handling for future provenance, fuzz/fault injection and documented threat model. Secrets/private keys must never be committed.

### Performance and resource behavior

Required: representative benchmark suites, resource budgets, regression thresholds and explicit hardware/backend metadata. Performance claims remain machine-dependent engineering evidence, never mathematical proof.

## Ranked continuation

1. Complete corrected v3.31 Python/native and v3.30 Lean/kernel qualification; accept only exact artifact-bound PASS evidence.
2. Normalize current repository/version truth and AI navigation; move historical diaries out of the README.
3. Harden Studio UX and recovery/failure behavior.
4. Implement no-code local-AI provider framework outside the evidence TCB.
5. Stabilize module/plugin SDK and `.cace` reproducibility contracts.
6. Build the certified FEM/PDE end-to-end research workflow with explicit theorem assumptions and certificates.
7. Audit/migrate the legacy scientific catalogue and remove unsupported maturity implications.
8. Qualify packaging/security/compatibility/performance for a production candidate.

See `docs/ROADMAP.md` for the milestone sequence and `docs/STATUS.md` for the current snapshot.
