# CACE Studio Current Status

Status date: 2026-09-15. Consolidated development candidate: `candidate/v336-consolidated`.

CACE is a research/development system. Production readiness is not established. Mathematical proof status, runtime verification, numerical evidence, provenance evidence and software maturity are intentionally tracked separately.

## Formal qualification boundary

The canonical claim `cace.v330.continuum-proof-strengthening` remains **not current-head qualified**. No runtime, documentation, provenance or signature layer may convert that state to formal PASS until an exact clean commit completes the pinned Lean build, kernel axiom audit and attestation process and the resulting commit/artifact binding is deliberately accepted into the canonical registry and proof ledger.

Historical GitHub/self-hosted attempts are infrastructure history only. None is qualification evidence. Formal qualification is now runner-independent through `make qualify-v330`, `scripts/qualify_v330_portable.sh`, and `Dockerfile.qualify-v330`.

The proof ledger records generic `qualification_system` + `qualification_run_id` provenance. `workflow_run_id` is optional except when GitHub Actions is itself the qualification system. The remaining v3.31 gate is therefore: successfully execute the portable qualifier on the exact clean candidate commit, verify the artifacts/digest, and accept only the exact earned claim/commit/artifact binding.

## Prepared v3.32-v3.36 candidate

The candidate development package version is `3.36.0.dev1`. It is intentionally unqualified.

Prepared areas include:

- v3.32 repository/version/AI onboarding normalization and deterministic repository indexes;
- v3.33 Studio UX hardening: typed drag/drop/click-connect editor, multi-select/delete, undo/redo, module search, zoom/fit, autosave/recovery, copy/paste, alignment, Proof Explorer, stale-evidence invalidation, selected+upstream scoped execution, asynchronous execution with cooperative pause/resume/cancel, and explicit unit metadata/compatibility;
- v3.34 optional local AI: Ollama, LM Studio, llama.cpp and generic loopback OpenAI-compatible servers, AI disabled by default, proxies disabled and redirects rejected;
- v3.35 versioned plugin SDK, fail-closed compatibility/trust checks, transactional plugin registration and runtime registry validation;
- v3.36 reproducibility/provenance: semantic/full graph fingerprints, source/execution-scope identity, report schema 4, canonical UTC evidence-ledger timestamps, content-addressed evidence bundles, Merkle identity, evidence ledger, Ed25519 signed attestations and fail-closed E5 evaluation;
- runner-independent formal qualification and generic qualification provenance.

Implementation is not qualification. The candidate has source/tests/static review but has not yet passed its required exact-head consolidated regression/formal qualification wave.

## v3.33 execution semantics

Full and selected-upstream executions now run against immutable graph snapshots. Selected-upstream execution computes the complete transitive upstream closure and records source graph hashes, executed graph hashes, target IDs, included IDs and a deterministic execution-scope SHA-256.

Studio execution is asynchronous. Pause/cancel is deliberately cooperative at module boundaries: CACE does not forcefully interrupt arbitrary scientific code inside a module. Cancelled/incomplete runs carry `completed=false` plus an interruption reason and can never satisfy `all_verifiers_passed`.

If the semantic graph changes while a worker runs, its result is not attached to the edited experiment. Starting a new run clears previously attached runtime evidence immediately.

## Units contract

Port and parameter units are optional canonical strings such as `m`, `s`, `m/s`, or `1`. CACE currently performs no implicit conversion. Two legacy unspecified-unit ports remain compatible; once either side declares a unit, both connected ports must declare the exact same unit. Unit declarations are visible in Studio and included in module-contract reproducibility fingerprints.

## Known remaining v3.33-v3.36 gaps

v3.33 now mainly lacks groups/subgraphs and minimap, plus actual GUI/cross-platform qualification. Future richer dimensional algebra/conversion must be explicit and versioned rather than silently changing the exact-match unit contract.

v3.35 still lacks a real third-party plugin sandbox/process-isolation layer, enforceable capability permissions, publisher signing/identity policy and production plugin lifecycle governance. Manifest trust labels are policy metadata, not a sandbox.

v3.36 implementation gaps are now mostly operational qualification/governance rather than missing provenance primitives: exact-head tests still need to run; production key management/verifier-independence policy remains later work.

## Immutable provenance status

The scientific-provenance layer is substantially implemented: content-addressed artifacts, deterministic bundles, canonical timestamps, signed verifier attestations, evidence-ledger structures and E5 policy/CLI support exist. These mechanisms authenticate identity and provenance only; they do not prove mathematics.

Still later-phase: production key-management policy, organizational verifier-independence policy, mature append-only transparency-log operations and optional anchoring to an established external timestamp/blockchain system. CACE must never require a token, cryptocurrency or blockchain connection for execution or mathematical rigor.

## Next dependency-ordered actions

1. Finish the last low-risk v3.33 Studio gaps (groups/subgraphs and minimap) without changing proof semantics.
2. Complete static portable-qualification contract tests/documentation and deterministic AI index generation readiness.
3. Execute `make qualify-v330` or Docker equivalent on the exact clean candidate commit.
4. If Lean build and axiom audit pass, verify the attestation and record only the exact earned claim/commit/artifact binding.
5. Run one consolidated native C++/Python/package/GUI/local-AI/plugin/reproducibility/provenance/E5 regression wave on the same exact head using any suitable local/container/external environment.
6. Re-run portable formal qualification after any qualification-sensitive fixes.
7. Fix exact-head regressions without weakening evidence policy.
8. Only after those gates pass, begin v3.37 certified FEM/PDE end-to-end integration.

## Remaining major roadmap

After current qualification/integration: v3.37 certified FEM/PDE; v3.38 Geometry/GA and legacy migration; v3.39 advanced research modules; v3.40 production engineering candidate; optional external provenance anchoring; then v4.0 only after the production definition of done is actually satisfied.

Open mathematical research obligations remain explicit. Conditional H1/H(div) bridge theorems do not become unconditional because surrounding infrastructure compiles. CACE must preserve theorem hypotheses and distinguish reductions/criteria from completed analytic constructions.

## Source of truth

For claims, use `cace_studio/data/claim_registry.json`, `cace_studio/data/proof_ledger.json` and `docs/CLAIMS.md`. For formal source, use `formal/cace_formal/`. For software behavior, use exact-commit test/run evidence. For project rules, use `docs/CONSTITUTION.md`. Historical release notes and failed infrastructure runs are context only and do not qualify current source.
