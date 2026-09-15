# CACE Studio Current Status

Status date: 2026-09-14. Live qualification branch: `implement/v331-truth-foundation`. Consolidated development candidate: `candidate/v336-consolidated`.

CACE is a research/development system. Production readiness is not established. Mathematical proof status, runtime verification, numerical evidence, provenance evidence and software maturity are intentionally tracked separately.

## Live v3.31 qualification boundary

The live qualification branch is intentionally kept separate from later engineering work. Its current purpose is to qualify the v3.23-v3.30 continuum proof-strengthening claim under the fail-closed claim registry/proof ledger policy.

Current formal qualification head: `0bbd9f42fdb4c4f50c4f83ff3b7955efb3155a08`.

The canonical claim `cace.v330.continuum-proof-strengthening` remains **not current-head qualified**. No runtime, documentation or provenance layer may convert that state to formal PASS until the exact source/workflow combination completes the pinned Lean build, kernel axiom audit and attestation process and the resulting exact commit/artifact binding is accepted into the canonical registry and ledger.

The formal workflow now uses a scoped Mathlib cache for `CACEFormal/V330AxiomAudit.lean` and its transitive import closure instead of downloading the full Mathlib cache. This was introduced after a prior self-hosted attempt exhausted runner disk before CACE theorem compilation.

The most recent exact-head formal attempt, GitHub Actions run `34916421854`, received the self-hosted runner and completed checkout and pinned Python setup, but the job terminated after approximately ten minutes while the governance-test step still had no step conclusion. It never reached Mathlib resolution or Lean compilation. This run is therefore an infrastructure/runner interruption, **not a theorem failure and not a successful qualification**.

A separate one-off maintenance branch, `maintenance/v331-runner-cleanup`, has cleanup run `34917238324` queued to remove only stale CACE formal temporary trees and report runner disk health. At this status update it has no runner assignment. Formal qualification cannot progress until a self-hosted runner is available again.

## Prepared v3.32-v3.36 candidate

Engineering work after the v3.31 boundary has been consolidated on `candidate/v336-consolidated`. It is intentionally unqualified and is not the live proof branch.

The candidate development package version is `3.36.0.dev1`. Implemented candidate areas include:

- v3.32 repository/version/AI onboarding normalization, including deterministic module/claim/proof/source index generation;
- v3.33 Studio UX hardening including editing history, autosave/recovery, canvas interaction improvements and evidence invalidation hooks;
- v3.34 optional local-AI provider infrastructure with AI disabled by default and loopback-focused security policy;
- v3.35 versioned module/plugin SDK and fail-closed compatibility/trust checks;
- v3.36 reproducibility fingerprints, content-addressed evidence bundles, Proof Explorer, evidence ledger, Ed25519 signed attestations and fail-closed E5 cross-verification evaluation;
- headless attestation commands for key generation, signing, signature verification and E5 evaluation;
- CI-cost hygiene that prevents selected obsolete historical hosted workflows from waking on development-only package/application changes.

These features have source/tests and static review, but the consolidated candidate has **not yet passed its required exact-head regression/formal qualification wave**. Implementation is not qualification.

## Immutable provenance status

The previously planned scientific-provenance layer is now partly implemented in the v3.36 candidate: content-addressed artifacts, deterministic evidence bundles, signed verifier attestations, evidence-ledger structures and E5 policy/CLI support exist. These mechanisms authenticate artifact identity and provenance only; they do not prove mathematical statements.

Still later-phase: production key-management policy, organizational verifier-independence policy, mature append-only transparency-log operations and optional anchoring to an established external timestamp/blockchain system. CACE must never require a token, cryptocurrency or blockchain connection for execution or mathematical rigor.

## Next dependency-ordered actions

1. Restore self-hosted runner availability and complete the isolated cleanup/disk-health job.
2. Re-run exact-head v3.31 formal qualification without changing theorem source merely to obtain a pass.
3. If Lean build and axiom audit pass, verify the generated attestation and record only the exact earned claim/commit/artifact binding in the canonical registry/ledger.
4. Integrate the consolidated v3.32-v3.36 candidate into the development line.
5. Run one consolidated native C++/Python/package regression plus formal requalification, because candidate `core/`, application and package changes intentionally invalidate inherited formal qualification.
6. Fix any exact-head regressions without weakening evidence policy.
7. Only after those gates pass, begin v3.37 certified FEM/PDE end-to-end integration.

## Remaining major roadmap

After the current qualification/integration gates: v3.37 certified FEM/PDE end-to-end; v3.38 Geometry/GA and legacy migration; v3.39 advanced research modules; v3.40 production engineering candidate; optional external provenance anchoring; then v4.0 only after the production definition of done is actually satisfied.

Open mathematical research obligations remain explicit. Conditional H1/H(div) bridge theorems do not become unconditional because surrounding infrastructure compiles. CACE must preserve theorem hypotheses and distinguish reductions/criteria from completed analytic constructions.

## Source of truth

For claims, use `cace_studio/data/claim_registry.json`, `cace_studio/data/proof_ledger.json` and `docs/CLAIMS.md`. For formal source, use `formal/cace_formal/`. For software behavior, use exact-commit test/run evidence. For project rules, use `docs/CONSTITUTION.md`. Historical release notes are context only and do not qualify current source.
