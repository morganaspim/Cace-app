# CACE v3.36 Consolidated Qualification Checklist

This checklist is an engineering gate, not verification evidence. A checked implementation item means source exists or static review was completed; it does not mean exact-head runtime/formal qualification has passed.

## Dependency gate

- [ ] v3.31 exact-head pinned Lean build passes.
- [ ] v3.31 kernel axiom audit passes.
- [ ] v3.31 formal attestation is verified and recorded in the canonical claim registry/proof ledger.
- [ ] Self-hosted runner is healthy enough to complete the consolidated regression and formal jobs.

Do not begin v3.37 scientific expansion until these prerequisites and the consolidated v3.36 qualification below are complete.

## Candidate identity

- Candidate branch: `candidate/v336-consolidated`
- Development package version: `3.36.0.dev1`
- Live proof branch remains separate: `implement/v331-truth-foundation`
- Candidate status: implemented/prepared, not qualified, not production-ready.

## v3.32 repository and AI readiness

- [x] Current architecture/status/roadmap documentation exists.
- [x] `AGENTS.md` defines rigor/evidence rules for connected AI agents.
- [x] `AI_REPO_MAP.json` identifies canonical truth sources and evidence boundaries.
- [x] Deterministic index generator exists for module, claim, proof-dependency and source indexes.
- [x] AI quickstart documents headless use and scoped formal qualification.
- [x] Development version normalized to `3.36.0.dev1` in package/runtime metadata.
- [ ] Generate all deterministic index outputs on exact candidate head.
- [ ] Run generator `--check` in qualification CI so committed/generated navigation cannot silently drift.

## v3.33 Studio UX

- [x] Editing history/undo-redo infrastructure prepared.
- [x] Canvas selection/deletion/zoom/search interaction improvements prepared.
- [x] Autosave/recovery infrastructure prepared.
- [x] Graph edits invalidate stale run evidence rather than preserving misleading PASS state.
- [x] Proof Explorer Studio integration prepared.
- [ ] Run GUI-focused tests on supported CI environment.
- [ ] Manual smoke qualification: drag/drop, click-connect, edit parameters, run, save/open `.cace`, recovery, Proof Explorer refresh.
- [ ] Cross-platform GUI packaging/launch qualification.

## v3.34 local AI

- [x] Optional provider abstraction prepared.
- [x] Local-provider GUI settings prepared.
- [x] AI disabled by default.
- [x] Loopback-oriented endpoint security restrictions prepared.
- [x] AI remains outside verification/proof promotion paths.
- [ ] Exact-head provider/security tests pass.
- [ ] Manual Ollama/local-compatible server health/model smoke test.
- [ ] Confirm AI-off Studio path has no local-model/network dependency.

## v3.35 module/plugin SDK

- [x] Versioned plugin manifest/SDK prepared.
- [x] Compatibility/trust checks fail closed.
- [x] Example plugin manifest exists.
- [ ] Exact-head SDK tests pass.
- [ ] Package-installed plugin discovery smoke test.
- [ ] Threat-model review for untrusted third-party plugins before production release.

## v3.36 reproducibility and evidence identity

- [x] Canonical deterministic JSON identity rejects unsupported/non-finite identity values.
- [x] Semantic/full experiment fingerprints prepared.
- [x] Module-contract fingerprinting prepared.
- [x] Content-addressed evidence artifacts prepared.
- [x] Deterministic artifact ordering and Merkle root prepared.
- [x] Bundle parser verifies declared Merkle root.
- [x] Artifact byte verification checks exact ID set, size and SHA-256.
- [x] Hash-chained evidence ledger prepared.
- [x] Ledger verification checks sequence, previous hash, entry hash and optional bundle/Merkle binding.
- [ ] Require canonical second-resolution UTC ledger timestamps (`YYYY-MM-DDTHH:MM:SSZ`) in both runtime validation and JSON schema. Current implementation only requires a non-empty ledger timestamp string; this is a deterministic-format hardening gap, not a hash-integrity failure.
- [ ] Exact-head evidence-ledger/reproducibility tests pass.
- [ ] Add/confirm serialized malformed-input and canonical-timestamp negative tests.

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

After v3.31 qualification is closed, integrate the candidate and run one bounded qualification wave:

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
11. [ ] Re-run pinned v3.30 formal workflow because candidate `core/`, `app.py` and package changes intentionally invalidate inherited qualification.
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
