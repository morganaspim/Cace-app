# CACE v3.36 Consolidated Qualification Checklist

This checklist is an engineering gate, not verification evidence. A checked implementation item means source exists or static review was completed; it does not mean exact-head runtime/formal qualification has passed.

## Dependency gate

- [ ] Exact-head pinned Lean build passes using the portable qualifier.
- [ ] Kernel axiom audit passes.
- [ ] Formal attestation is verified and recorded in the canonical claim registry/proof ledger.
- [x] Qualification no longer depends on a self-hosted or GitHub-hosted runner.
- [x] Generic qualification provenance (`qualification_system` + `qualification_run_id`) is supported fail-closed.

Do not begin v3.37 scientific expansion until these prerequisites and the consolidated v3.36 qualification below are complete.

## Candidate identity

- Candidate branch: `candidate/v336-consolidated`
- Development package version: `3.36.0.dev1`
- Candidate status: implemented/prepared, not qualified, not production-ready.
- Canonical portable qualification entry points: `make qualify-v330`, `scripts/qualify_v330_portable.sh`, `Dockerfile.qualify-v330`.

## v3.32 repository and AI readiness

- [x] Current architecture/status/roadmap documentation exists.
- [x] `AGENTS.md` defines rigor/evidence rules for connected AI agents.
- [x] `AI_REPO_MAP.json` identifies canonical truth sources and evidence boundaries.
- [x] Deterministic index generator exists for module, claim, proof-dependency and source indexes.
- [x] AI quickstart documents headless use and scoped formal qualification.
- [x] Development version normalized to `3.36.0.dev1` in package/runtime metadata.
- [ ] Generate all deterministic index outputs on exact candidate head.
- [ ] Run generator `--check` on the exact candidate head so generated navigation cannot silently drift.

## v3.33 Studio UX

- [x] Editing history/undo-redo infrastructure prepared.
- [x] Canvas selection/deletion/zoom/search interaction improvements prepared.
- [x] Autosave/recovery infrastructure prepared.
- [x] Graph edits invalidate stale run evidence rather than preserving misleading PASS state.
- [x] Proof Explorer Studio integration prepared.
- [x] Deterministic selected-fragment copy/paste prepared with fresh node IDs and internal-edge preservation.
- [x] Basic alignment operations prepared with rollback-safe model/canvas restoration.
- [x] Selected + transitive-upstream execution prepared with source/executed graph hashes, target IDs, included-node IDs and execution-scope SHA-256.
- [x] Graph execution moved off the GUI thread through a snapshot-based worker.
- [x] Cooperative pause/resume/cancel prepared at module boundaries.
- [x] Incomplete/cancelled runs cannot satisfy `all_verifiers_passed` and record explicit interruption state.
- [x] Results from a stale semantic graph snapshot are not attached to an edited experiment.
- [x] Explicit port/parameter unit metadata prepared with exact-match fail-closed connection policy and no implicit conversion.
- [x] Unit declarations are visible in Studio and included in module-contract fingerprints.
- [ ] Add groups/subgraphs.
- [ ] Add minimap.
- [ ] Run GUI-focused tests on a supported execution environment.
- [ ] Manual smoke qualification: drag/drop, click-connect, unit mismatch rejection, edit parameters, copy/paste, align, full/scoped run, pause/resume/cancel, save/open `.cace`, recovery, Proof Explorer refresh.
- [ ] Cross-platform GUI packaging/launch qualification.

## v3.34 local AI

- [x] Optional provider abstraction prepared.
- [x] Local-provider GUI settings prepared.
- [x] AI disabled by default.
- [x] Ollama, LM Studio, llama.cpp and generic OpenAI-compatible local providers prepared.
- [x] Loopback-only endpoint security restrictions prepared.
- [x] Environment proxies disabled and redirects refused for local-AI transport.
- [x] AI remains outside verification/proof promotion paths.
- [ ] Exact-head provider/security tests pass.
- [ ] Manual Ollama/local-compatible server health/model smoke test.
- [ ] Confirm AI-off Studio path has no local-model/network dependency.

## v3.35 module/plugin SDK

- [x] Versioned plugin manifest/SDK prepared.
- [x] Compatibility/trust checks fail closed.
- [x] Example plugin manifest exists.
- [x] Plugin registration is transactional: failed registration cannot partially mutate the live registry.
- [x] Core registry rejects non-Module classes, blank/whitespace IDs and duplicate IDs before mutation.
- [x] SDK documents explicit units as contract metadata rather than automatic conversion.
- [ ] Exact-head SDK tests pass.
- [ ] Package-installed plugin discovery smoke test.
- [ ] Add real process isolation/sandboxing for untrusted third-party code before production use.
- [ ] Define enforceable capability permissions and publisher identity/signing policy.
- [ ] Threat-model review for untrusted third-party plugins before production release.

## v3.36 reproducibility and evidence identity

- [x] Canonical deterministic JSON identity rejects unsupported/non-finite identity values.
- [x] Semantic/full experiment fingerprints prepared.
- [x] Every prepared `RunResult` binds source and executed graph fingerprints, seed and execution scope.
- [x] Run-report schema 4 commits source/executed graph identity, scope identity and completion/interruption state.
- [x] Module-contract fingerprinting includes port/parameter unit declarations.
- [x] Content-addressed evidence artifacts prepared.
- [x] Deterministic artifact ordering and Merkle root prepared.
- [x] Bundle parser verifies declared Merkle root.
- [x] Artifact byte verification checks exact ID set, size and SHA-256.
- [x] Hash-chained evidence ledger prepared.
- [x] Ledger verification checks sequence, previous hash, entry hash and optional bundle/Merkle binding.
- [x] Canonical second-resolution UTC ledger timestamps (`YYYY-MM-DDTHH:MM:SSZ`) are required in runtime validation and JSON schema.
- [x] Malformed/canonical-timestamp negative tests are staged.
- [ ] Exact-head evidence-ledger/reproducibility/execution-scope/control/unit tests pass.

## Portable formal qualification

- [x] Qualification semantics are independent of GitHub Actions and any single runner.
- [x] Exact commit and clean-tree requirements are enforced before attestation generation.
- [x] Pinned Lean toolchain and exact Mathlib commit are required.
- [x] Mathlib cache retrieval is scoped to `CACEFormal/V330AxiomAudit.lean` transitive imports.
- [x] `sorry`, `admit` and `OPEN OBLIGATION` tokens are rejected in the audited source set.
- [x] `sorryAx` and non-whitelisted axioms are rejected by the standalone auditor.
- [x] Attestation binds exact commit, qualification system/run, source-bundle hash, axiom-audit hash, Lean version and Mathlib commit.
- [x] Docker is only an environment wrapper around the same portable procedure, not a second proof policy.
- [ ] Run `make qualify-v330` or Docker equivalent successfully on the exact candidate head.
- [ ] Review generated `v330_formal_qualification_attestation.json` and its SHA-256 before canonical promotion.

## Signed attestations

- [x] Ed25519 selected via vetted `cryptography` implementation; no custom signature primitive.
- [x] Signature statements use domain-separated canonical bytes.
- [x] Public-key identity is SHA-256 over raw Ed25519 public key.
- [x] Signed envelope verifies statement digest, embedded public-key identity and signature.
- [x] Canonical second-resolution UTC attestation timestamps enforced.
- [x] Parser rejects unknown envelope/statement fields.
- [x] Attestation operations declare `proof_effect: none`.
- [x] Console key generation refuses accidental output collisions/aliasing.
- [x] Optional attestation dependency has an explicit installation error path.
- [ ] Exact-head signing/verification/CLI tests pass in wheel-installed environment.
- [ ] Define production private-key storage/rotation/revocation policy before production use.

## E5 cross-verification

- [x] E5 cannot create mathematical qualification.
- [x] Canonical registry claim must already be current-head PASS qualified.
- [x] Canonical proof-ledger entry must already be current-head PASS qualified.
- [x] Registry/ledger qualified commit and proof-artifact hash must agree.
- [x] Attestation must bind exact claim, evidence bundle, qualified commit and proof artifact.
- [x] Only explicitly approved verifier-key/identity bindings count.
- [x] Duplicate signed statements do not count twice.
- [x] Multiple keys for one verifier identity do not create independence.
- [x] One key presented as multiple identities cannot satisfy distinct-key requirement.
- [x] Minimum E5 policy requires at least two distinct approved identities and two distinct approved keys.
- [x] E5 result explicitly retains `proof_effect: none`.
- [ ] Exact-head E5 negative/positive tests pass.
- [ ] Production governance must define verifier identity and organizational independence outside mere key possession.

## Consolidated regression gate

The exact candidate head must pass one bounded qualification wave in any suitable local, container or external execution environment; GitHub Actions is optional:

1. [ ] Native C++ CMake build passes.
2. [ ] Native CTest passes.
3. [ ] Full Python test suite passes.
4. [ ] Focused GUI/local-AI/plugin/reproducibility/provenance/E5 tests pass.
5. [ ] Qualification-drift audit behaves fail-closed.
6. [ ] Wheel builds successfully.
7. [ ] Wheel installs into a clean environment.
8. [ ] Installed `cace` registry/headless interface passes.
9. [ ] Installed `cace-attest` behavior is checked both without and with the optional attestation dependency.
10. [ ] Deterministic AI indexes generate and `--check` cleanly.
11. [ ] Portable v3.30 qualification runs on the same exact head after any qualification-sensitive fixes.
12. [ ] Kernel axiom audit passes on the integrated exact head.
13. [ ] Exact-head formal attestation is verified and canonical ledger/registry entries are updated only to the evidence actually earned.

## Production blockers intentionally outside v3.36

- v3.37 certified FEM/PDE end-to-end integration.
- v3.38 Geometry/GA and legacy feature migration.
- v3.39 advanced research-module qualification.
- v3.40 packaging/security/platform/performance/release engineering.
- Production verifier identity/key governance and transparency-log operations.
- Optional established external timestamp/blockchain anchoring.
- v4.0 production designation only after the full production definition of done is satisfied.
