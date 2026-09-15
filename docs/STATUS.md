# CACE Studio Current Status

Status date: 2026-09-15. Consolidated development candidate: `candidate/v336-consolidated`.

CACE is a research/development system. Production readiness is not established. Mathematical proof status, runtime verification, numerical evidence, provenance evidence and software maturity are intentionally tracked separately.

## Formal qualification boundary

The canonical claim `cace.v330.continuum-proof-strengthening` remains **not current-head qualified**. No runtime, documentation, provenance or signature layer may convert that state to formal PASS until an exact clean commit completes the pinned Lean build, kernel axiom audit and attestation process and the resulting commit/artifact binding is deliberately accepted into the canonical registry and proof ledger.

Historical GitHub/self-hosted attempts are retained only as infrastructure history. One self-hosted attempt exhausted disk before theorem compilation, a later self-hosted attempt terminated before reaching Lean, and a GitHub-hosted fallback job terminated before its first workflow step. None of those runs is a theorem failure and none is qualification evidence.

Formal qualification is now runner-independent. The candidate contains the canonical portable path:

- `make qualify-v330`
- `bash scripts/qualify_v330_portable.sh`
- `Dockerfile.qualify-v330`
- `scripts/audit_v330_axioms.py`
- `scripts/write_v330_qualification_attestation.py`
- `docs/PORTABLE_QUALIFICATION.md`

The proof-ledger model now records generic `qualification_system` + `qualification_run_id` provenance. `workflow_run_id` remains optional metadata except when GitHub Actions is itself the qualification system. Historical GitHub ledger entries remain backward-compatible.

The remaining v3.31 gate is therefore straightforward: execute the portable qualifier successfully on the exact clean candidate commit, verify its output artifacts and SHA-256 digest, and accept only the exact earned claim/commit/artifact binding into the canonical claim registry and proof ledger.

## Prepared v3.32-v3.36 candidate

Engineering work after the original v3.31 boundary has been consolidated on `candidate/v336-consolidated`. It is intentionally unqualified.

The candidate development package version is `3.36.0.dev1`. Implemented/prepared areas include:

- v3.32 repository/version/AI onboarding normalization, including deterministic module/claim/proof/source index generation;
- v3.33 Studio UX hardening: drag/drop and typed click-connect editor, multi-select/delete, undo/redo, module search, zoom/fit, autosave/recovery, graph-fragment copy/paste, alignment tools, Proof Explorer integration and stale-evidence invalidation;
- v3.34 optional local-AI providers including Ollama, LM Studio, llama.cpp and generic OpenAI-compatible loopback servers, with AI disabled by default and remote/proxy/redirect escape paths rejected;
- v3.35 versioned module/plugin SDK, fail-closed compatibility/trust checks, transactional plugin registration and runtime registry contract validation;
- v3.36 deterministic reproducibility fingerprints, content-addressed evidence bundles, Merkle identity, evidence ledger, run/report graph fingerprint binding, Proof Explorer, Ed25519 signed attestations and fail-closed E5 cross-verification evaluation;
- headless attestation commands for key generation, signing, signature verification and E5 evaluation;
- runner-independent formal qualification and generic qualification provenance;
- CI-cost hygiene preventing selected obsolete historical workflows from waking on development-only changes.

These features have source/tests/static review, but the consolidated candidate has **not yet passed its required exact-head regression/formal qualification wave**. Implementation is not qualification.

## Known remaining v3.33-v3.36 gaps

v3.33 still lacks the higher-risk production-pass items: selected/upstream subgraph execution with explicit scope identity, asynchronous execution/cancel/pause, groups/subgraphs, explicit units and minimap. These should not be added by bypassing deterministic execution/provenance semantics.

v3.35 still lacks a real third-party plugin sandbox/process-isolation layer, enforceable capability permissions, publisher signing/identity policy and production plugin lifecycle governance. Manifest trust labels are policy metadata, not a sandbox.

v3.36 still has one explicit deterministic-format hardening gap: evidence-ledger timestamps should require canonical second-resolution UTC `YYYY-MM-DDTHH:MM:SSZ` in runtime validation and JSON schema. The current non-empty timestamp check does not weaken the existing hash-chain integrity, but canonical timestamp formatting should be completed before v3.36 exit.

## Immutable provenance status

The scientific-provenance layer is substantially implemented in the candidate: content-addressed artifacts, deterministic evidence bundles, signed verifier attestations, evidence-ledger structures and E5 policy/CLI support exist. These mechanisms authenticate artifact identity and provenance only; they do not prove mathematical statements.

Still later-phase: production key-management policy, organizational verifier-independence policy, mature append-only transparency-log operations and optional anchoring to an established external timestamp/blockchain system. CACE must never require a token, cryptocurrency or blockchain connection for execution or mathematical rigor.

## Next dependency-ordered actions

1. Finish static/low-risk v3.36 hardening, especially canonical evidence-ledger timestamps and portable-qualification contract tests.
2. Execute `make qualify-v330` or the Docker equivalent on the exact clean candidate commit.
3. If Lean build and axiom audit pass, verify the generated attestation and record only the exact earned claim/commit/artifact binding in the canonical registry/ledger.
4. Run one consolidated native C++/Python/package/GUI/local-AI/plugin/reproducibility/provenance/E5 regression wave on the exact candidate head using any available local or external execution environment; GitHub Actions is optional.
5. Re-run the portable formal qualifier after any qualification-sensitive fixes.
6. Fix exact-head regressions without weakening evidence policy.
7. Only after those gates pass, begin v3.37 certified FEM/PDE end-to-end integration.

## Remaining major roadmap

After the current qualification/integration gates: v3.37 certified FEM/PDE end-to-end; v3.38 Geometry/GA and legacy migration; v3.39 advanced research modules; v3.40 production engineering candidate; optional external provenance anchoring; then v4.0 only after the production definition of done is actually satisfied.

Open mathematical research obligations remain explicit. Conditional H1/H(div) bridge theorems do not become unconditional because surrounding infrastructure compiles. CACE must preserve theorem hypotheses and distinguish reductions/criteria from completed analytic constructions.

## Source of truth

For claims, use `cace_studio/data/claim_registry.json`, `cace_studio/data/proof_ledger.json` and `docs/CLAIMS.md`. For formal source, use `formal/cace_formal/`. For software behavior, use exact-commit test/run evidence. For project rules, use `docs/CONSTITUTION.md`. Historical release notes and failed infrastructure runs are context only and do not qualify current source.
