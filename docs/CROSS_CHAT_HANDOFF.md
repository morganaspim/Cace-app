# CACE Cross-Chat Handoff

Status: continuity/navigation document only. It is **not proof, qualification, production-readiness, or scientific evidence**.

Last refreshed: 2026-09-19.

## Standing continuity directive

Every CACE chat or connected agent should be able to continue without asking the user to reconstruct prior work from memory.

For every new CACE chat:

1. Retrieve this file and `docs/CHAT_IDEA_LEDGER.md`.
2. If ChatGPT Library access is available, search for the mirrored files:
   - `/CACE CONTINUITY/CACE_CROSS_CHAT_HANDOFF.md`
   - `/CACE CONTINUITY/CACE_CHAT_IDEA_LEDGER.md`
3. Read `CACE_AGENT_BOOTSTRAP.json`, `docs/GOAL_REGISTRY.json`, and the relevant current proof/feature roadmap.
4. Re-query live GitHub branch, PR, commit, and Actions state before taking any proof/deployment action. A snapshot in this file may be stale.
5. Continue from the highest-value live gate without asking the user to repeat already-preserved context.

For every substantive CACE chat before a natural stopping point:

1. identify new user ideas/goals with mathematical, scientific, product, reliability, proof-rigor, security, visualization, AI, deployment, or workflow merit;
2. deduplicate them against `docs/GOAL_REGISTRY.json` and `docs/CHAT_IDEA_LEDGER.md`;
3. append specific novel ideas to the idea ledger;
4. update the goal registry/master spec when the idea changes durable implementation intent;
5. refresh the exact live handoff state when a proof/CI/deployment gate changes;
6. mirror the current handoff and idea ledger to ChatGPT Library when available;
7. never convert documentation, AI agreement, historical logs, or a handoff snapshot into proof evidence.

This is a standing CACE workflow preference.

## Source-of-truth hierarchy

Use this order rather than treating the handoff as authority:

- current checked-out / queried Git commit for source;
- `formal/cace_formal/` for formal statements;
- `cace_studio/data/claim_registry.json` and `cace_studio/data/proof_ledger.json` for canonical formal claim status;
- exact-current-head Actions/qualification artifacts for proof qualification evidence;
- `docs/GOAL_REGISTRY.json` and `docs/MASTER_BUILD_SPEC.md` for durable implementation intent;
- `docs/CHAT_IDEA_LEDGER.md` for preserved research/product ideas that may not yet be scheduled;
- this file for continuity and next-step navigation.

## Redundant preservation surfaces

### 1. GitHub repository

Canonical continuity files:

- `docs/CROSS_CHAT_HANDOFF.md`
- `docs/CHAT_IDEA_LEDGER.md`
- `docs/GOAL_REGISTRY.json`
- `docs/MASTER_BUILD_SPEC.md`
- `CACE_AGENT_BOOTSTRAP.json`

### 2. ChatGPT Library

Mirror the two self-contained continuity documents under:

`/CACE CONTINUITY/`

This is the primary cross-chat fallback if GitHub is unavailable to a future chat.

Operational mirror status (2026-09-19): the `/CACE CONTINUITY/` Library folder was created, but this session's generated-file upload bridge returned `container_session_unavailable`, so **do not assume the two current mirror files are present yet**. The exact current files remain in GitHub and in the generating chat as downloadable artifacts. A future CACE chat with a working Library write surface should retry the mirror and then update this status.

### 3. Existing historical Library corpus

Useful recovery sources include:

- `CACE_MASTER_TIMELINE_FEATURES_MATH_PROOFS_IDEAS_2026-09-17.txt`
- `CACE_FULL_REMAINING_PLAN_2026-09-14.txt`
- `CACE_EXACT_CONTINUATION_HANDOFF_2026-09-16.txt`
- `CACE_PROGRAM_GOALS_STATUS_2026-09-16.txt`
- `INFINITE_EXTENSION.md`
- `THEORY.md`

These are historical/context sources only; current code/proof status must be re-verified.

## Current proof handoff snapshot

Snapshot timestamp: 2026-09-19 20:11 UTC. **Re-query live state before acting.**

### Durable CI infrastructure

PR #47, “CI: batch quarantined theorem preflight to minimize user dispatches”, was merged to `main`.

Merged commit:

`7c3bbe8cc744b9ed9c7ead6f1a5fdf308e790b1c`

Durable behavior includes:

- batched quarantined theorem preflight;
- self-validating Lean-source sanity;
- required sentinel scanning;
- stronger standalone-quarantine protections;
- regression-tested CACE Actions serialization;
- provider-independent local evidence retention for source-sanity runs.

### Current formal theorem batch

Roadmap:

`docs/proofs/V341_TOP20_OF50_THEOREM_ROADMAP.md`

Partition:

- v3.41A ranks 1–8
- v3.41B ranks 9–14
- v3.41C ranks 15–16
- v3.41D ranks 17–19
- v3.41E rank 20

v3.41A branch:

`proof/v3.41a-box-zero-boundary-core`

Current promoted head:

`f13b63c02c74209f3e47a88ab11ed7b4a1e33c72`

PR:

#42 — “Draft: v3.41A construct smooth box zero-boundary core”

Standalone Exact-Pin passed earlier on pre-promotion head:

`4465586eff2c606ebcfb0fbc11c853ea6ddc88f5`

Audited-root Exact-Pin run:

`35466492951`

Result: **SUCCESS** at exact head `f13b63c02c74209f3e47a88ab11ed7b4a1e33c72`.

The successful audited-root run passed:

- exact-head isolation;
- serialization;
- requested-target/root reachability;
- permanent proof guardrails and frozen plan;
- malformed-source rejection;
- pinned Lean/Mathlib restore;
- cache-local verification;
- proof API canaries;
- impacted-module and reverse-dependent compilation;
- requested `BoxZeroBoundaryCore` compilation;
- frozen-plan recheck;
- full audited-root compilation;
- aggregate diagnostic gate;
- evidence upload.

### v3.41A mathematical scope

Implemented/promoted module:

`CACEFormal/BoxZeroBoundaryCore.lean`

It constructs an explicit smooth face-vanishing scalar core and proves the corresponding zero classical face flux / normal-trace pairing for smooth vector fields.

Preserve these nonclaims:

- it does **not** yet extend the cancellation to every closed-graph H(div) test;
- it does **not** identify the graph closure with every textbook presentation of H_0^1;
- it does **not** prove arbitrary box H1 fields have zero trace;
- documentation or successful preflight alone is not canonical formal qualification.

### Next formal gate

Before beginning v3.41B promotion, perform the normal **canonical exact-current-head qualification** for the v3.41A promoted head and verify the emitted kernel/metadata/proof-contract/provenance evidence.

If canonical qualification passes, preserve/promote exact provenance and then proceed to v3.41B ranks 9–14:

- fixed-test-field normal-trace continuous functional;
- dense-flux-core annihilation -> functional zero boundary trace;
- embedded smooth face-vanishing scalar -> functional zero trace;
- smooth-to-closed H1 graph linear map;
- concrete boundary-vanishing smooth graph core;
- core inclusion in the functional zero-boundary submodule.

## CI / proof operating rules

- Do cheap/static/local checks before spending an OCI Lean run.
- Serialize expensive CACE proof jobs.
- Do not retry unchanged failures.
- Convert each discovered failure class into a regression guard where practical.
- Cache work, never truth.
- Do not weaken theorem statements, proof scope, negative tests, or canonical gates to get green CI.
- Prefer batched standalone proof preflight for multiple quarantined modules when rigor is unchanged.
- Exact-current-head canonical qualification remains separate from preflight.

## Cross-chat update rule

A future CACE chat that materially changes any of the following should refresh this handoff:

- active theorem/proof frontier;
- exact head/PR/run IDs;
- current deployment gate;
- durable architecture;
- new meritorious user goals;
- novel mathematical/research ideas;
- CI/proof safety rules;
- major feature completion or removal.

The goal is continuity without making conversational memory part of the trusted computing base.


## New local-AI reasoning direction

Added 2026-09-19.

Design document:

`docs/LOCAL_AI_REASONING_CURRICULUM.md`

New durable goals:

- G048 — reasoning-first local AI curriculum and anti-memorization evaluation;
- G049 — Conway-inspired canvas/local-AI heartbeat field.

Core intent:

- teach reusable typed operations and operation order rather than memorized answers;
- procedural generation + held-out structural compositions;
- canonical/load-bearing perturbation pairs where answers must change;
- irrelevant/symmetry perturbations where answers must remain invariant;
- external executable operator-plan checks rather than hidden chain-of-thought dependence;
- geometric/relational structure, invariants and sparse operator programs rather than brute-force all-pairs association;
- deterministic canvas heartbeat states that guide AI attention but can never promote verification.


## Molecular / protein / materials / physics expansion

Added 2026-09-19.

Design document:

`docs/MOLECULAR_PROTEIN_MATERIALS_PHYSICS.md`

New durable goals:

- G050 — typed atoms/molecules + safe home-lab chemistry;
- G051 — AlphaFold-compatible import + low-cost protein fold search;
- G052 — mathematical materials screening;
- G053 — draggable physics objects.

Key nonclaims:

- AlphaFold predicts structures; it is not treated as a novel-sequence generator.
- CACE fold search reports the lowest energy **found**, never a proven global protein-energy minimum.
- AlphaFold 3 weights are not bundled without separate terms review.
- material candidates are hypotheses/screening results, not experimentally discovered materials;
- Safe Home Lab is whitelist-only and fails closed for hazardous chemistry;
- string/brane objects are theoretical visualization objects, not experimentally established particles.


### Molecular/materials implementation frontier

Draft PR #48: `Science: molecular, protein folding, materials, and physics canvas modules`

Branch: `feature/molecular-materials-physics`

Head: `65bc547548f15e1aa4bcf9e5c56a6397b8a11e1d`

Current validation:
- local isolated scientific behavior suite: 6/6 passed;
- CACE Collaboration Coordination Validation run `35469238744`: SUCCESS at exact PR head;
- no Lean/proof qualification job was triggered;
- full repository Python/native regression has **not** yet been run for this feature branch.

Implemented baseline:
- typed Atom/Bond/Molecule objects;
- direct Protein Sequence canvas source;
- AlphaFold-compatible PDB C-alpha import with source/license/attribution/content hash;
- deterministic low-cost C-alpha fold search with `global_minimum_claim=false`;
- strict Safe Home Lab whitelist;
- deterministic materials descriptor screening with no synthesis instructions;
- established/theoretical physics canvas objects including quarks and string/worldsheet/brane research objects.

Do not merge/describe this as production-ready solely from the narrow validation above. The next quality gate is a deliberate broader Python/native regression or an equivalent local full test run.


## Open Problems Toolkit

Added 2026-09-19.

Design:

`docs/OPEN_PROBLEMS_TOOLKIT.md`

Durable goal:

- G054 — source-backed, date-stamped Open Problems Toolkit with canvas import + heartbeat/local-AI Play.

V1 policy:

- seed catalog: Clay Millennium Prize Problems;
- current snapshot verified 2026-09-19: five listed open, Navier–Stokes active-review after Clay's apparent-settlement announcement, and Poincaré solved;
- catalog is offline-first and stores source URLs as provenance metadata;
- imported problems are typed research objects, never verification evidence;
- Play may generate hypotheses/decompositions/experiments/proof obligations but cannot mark an open problem solved.

Protein clarification also preserved as I065: use attributable imported protein structures and heartbeat/AI Play; do not reproduce AlphaFold.


## Heartbeat economy and AI capability controls

Added 2026-09-19.

New goals:

- G055 — Conway heartbeat spare-compute economy;
- G056 — default-off superintelligence-class capability gate;
- G057 — immutable one-way deep-layer matrix observers.

Design invariants:

- compute credits are an internal scheduling game only, with no monetary value and no evidence authority;
- AI cannot reward itself; scheduler optimization uses externally measured completion/cost/latency data;
- the high-capability checkbox is a provider-admission control, not a proof that an unchecked model is incapable of superintelligence;
- enabling the gate does not automatically grant Internet, shell, self-modification, evidence mutation, or unbounded compute;
- hidden-layer observers only apply to engines that expose activations;
- layer/step matrices flow one-way into at least two host-controlled observer replicas with no feedback channel to inference.


## Math Coin heartbeat economic city

Added 2026-09-19.

Durable goal:

- G058 — fixed-supply Math Coin burn-to-compute economy layered above the internal non-monetary heartbeat credits.

Core economics:

- maximum/genesis supply: exactly 500,000,000,000 MATH;
- no mining, staking reward, or block-reward issuance;
- most genesis supply remains in a time-locked vault;
- circulating-supply expansion can occur only through explicit all-at-once vault tranches at 10-year boundaries;
- exact tranche sizes remain explicit constitutional parameters and cannot be changed by the AI;
- AI/user compute demand reserves MATH first and burns the reserved amount only after host-measured computation settles;
- failed/cancelled computation must not create a valid burn receipt.

Architecture:

- CACE internal compute credits remain fast, non-monetary scheduler credits;
- MATH is a separate scarce external compute-right/market layer;
- the Conway heartbeat "economic city" may contain AI agents, compute providers, markets, wallets, resource districts, and trade/compute flows;
- agents can propose/trade MATH against real crypto only through a narrow broker; agents never receive raw private keys;
- per-agent budgets, asset allowlists, exposure limits, kill switches, deterministic audit records, and rate limits are mandatory;
- because compute-purchase MATH is burned, provider compensation is a separate settlement leg rather than pretending the burned token can also be delivered to the provider;
- economic/market state never changes proof/evidence truth.

Research document:

`docs/MATH_COIN_HEARTBEAT_ECONOMY.md`


### AlphaFold DB API import + heartbeat path

Added 2026-09-19.

Current public API contract used by CACE:

`GET https://alphafold.com/api/prediction/{UniProt-accession}`

CACE consumes the post-2026 metadata field names such as `modelEntityId`, `sequence`, `sequenceStart`, and `sequenceEnd`, while retaining old field names only as a defensive backwards-compatibility fallback. The API-supplied `pdbUrl` is used rather than constructing/version-guessing a file name.

Security/provenance:

- accession is canonicalized/validated;
- metadata and PDB downloads are byte-size bounded;
- metadata/PDB URLs must remain HTTPS on approved AlphaFold domains;
- PDB content receives a SHA-256 provenance hash;
- source entry, API URL, model entity/version metadata, CC-BY-4.0 license, and AlphaFold DB attribution are retained;
- import verification proves retrieval/schema/hash/license/attribution integrity only, not correctness of the predicted fold.

Implementation:

- PR #48 exact API implementation head: `a23a153f984f5dbb3b6827bef84e95a50c8fcaf4`;
- module ID: `protein.alphafold_api_import`;
- API client: `cace_studio/integrations/alphafold_db.py`;
- typed outputs: `protein_sequence` + `protein_structure`.

GUI/heartbeat:

- PR #50 adds **AlphaFold DB → Canvas + Fetch** to Protein Playground;
- it creates the API import node, selects it, and starts Selected + Upstream execution;
- after completion, Protein Playground discovers the returned `protein_structure`;
- **Play Selected Protein with Local AI** applies residue-level + source-node heartbeats without mutating the imported structure.

The two PRs remain separated by responsibility: #48 owns scientific/API objects; #50 owns heartbeat/AI/GUI control integration.


## Rigorous AI builder foundation

Added 2026-09-19 on documentation branch `docs/rigorous-builder-foundation-v1`.

New governance/specification files:

- `CACE_AI_BUILDER_CONTRACT.md` — Gemini AI Code Studio is the preferred primary implementation environment, but AI remains outside evidence authority and must preserve the existing proof/qualification architecture.
- `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md` — defines FSL-0..FSL-13 from canonical runtime packet through exact P1/RT0 discrete binding and onward to explicit H1/H(div)/`volumePairing` continuum linkage.

New durable goals:

- G059 — Gemini-first AI builder contract with evidence isolation.
- G060 — concrete runtime-to-formal P1/RT0 and continuum linkage.

Key preserved nonclaim: exact discrete P1/RT0 identities and qualified generic continuum theorems do not automatically establish that arbitrary runtime finite-element fields satisfy the continuum graph-space/Green-pairing hypotheses. Missing source-to-formal links remain unresolved/NOT_RUN.

This builder-foundation branch is documentation/governance only; it does not itself qualify any theorem or runtime bridge.


## Rigorous Math Kernel -> Math Toolbox -> Science completeness program

Added 2026-09-19 after the Gemini web-boundary handoff was merged.

The user explicitly chose to strengthen CACE's mathematical capability before substantial Google AI Studio web implementation.

New design documents:

- `docs/CACE_RIGOROUS_MATH_KERNEL_V1.md`
- `docs/PROOF_BACKED_MATH_TOOLBOX_ROADMAP.md`
- `docs/SCIENCE_MODULE_COMPLETENESS_STANDARD.md`

New durable goals:

- G061 — CACE Rigorous Math Kernel v1;
- G062 — broad proof-backed mathematical toolbox;
- G063 — full-featured composable science modules;
- G064 — integrated Help pages + runnable example library.

Implementation order:

```text
RMK-v1
  -> canonical proof-backed Math Toolbox
  -> full-featured composable Science Modules
  -> structured Help + tested examples
  -> substantial Gemini browser presentation polish
```

Gemini queue change:

- `gemini/CACE_GEMINI_TASK_STATE.json` now makes **RMK-1** the first task.
- GWEB-1 is deferred until the math/API foundation is stable enough.
- Minimal web/API scaffolding is still allowed if it does not freeze unstable scientific interfaces.

RMK-1 target:

- canonical exact rational/scalar arithmetic in C++;
- exact vector primitives;
- deterministic canonical math packets + semantic hashes;
- thin Python bindings;
- malformed/overflow/adversarial tests;
- no change to formal proof status from implementation alone.

Math toolbox direction:

- migrate away from proliferating historical version-number wrappers;
- use semantic canonical module IDs;
- reuse existing Lean theorem families only through explicit runtime bindings;
- show evidence badges distinguishing FORMAL, EXACT, INTERVAL, SYMBOLIC, NUMERICAL, REVIEWED and EXPERIMENTAL.

Science-module direction:

- shared typed objects and units;
- real module-to-module interoperability;
- appropriate verifiers/certificates;
- Help pages and runnable examples;
- approximately 100 curated high-value examples as a long-term target.

This program is architecture/implementation intent only and does not alter existing proof qualification state.


## 2026-11-13 continuity and runner operations update

The canonical Merlin/CACE cross-agent handoff is now `docs/MERLIN_PRODUCTION_HANDOFF.md`. Every AI/chat/agent must read it before work, then re-query live GitHub state. It records the Merlin architecture and product goals, authority/security invariants, active PR chain, exact validation commits/runs, mathematical gates, bug-to-guardrail lifecycle, and next actions. It is a navigation snapshot, never proof evidence.

Runner setup and operational safety are documented in `docs/OCI_RUNNER_OPERATIONS.md`. It covers the existing `cace-oci-a1` self-hosted lane, labels, ARM64 architecture, loopback-only OCI MCP service, least-privilege instance-principal model, safe replacement-runner procedure, health checks, resource gates, and recovery. Archived provisioning scripts are historical only; in particular, the archived unrestricted `ocarun` sudo grant must never be reused.

Both documents are first-read entries in `CACE_AGENT_BOOTSTRAP.json` and linked from the repository README. The latest PR #102 head validation is run #655, exact head `a9b8a9c661c7271e40d8927c1622c67ced52ccdb`, successful engineering-only validation. Re-query current PR and run state before any action. PR #102 remains stacked on PR #101 and must not merge independently.


## 2026-11-13 Merlin math continuation

Read `docs/MERLIN_PRODUCTION_HANDOFF.md` first for the full canonical state. The F-031 proof-hole guard now has a second layer: `scripts/check_lean_source_sanity.py` masks comments/strings and scans the complete `formal/cace_formal` tree for whole-token `sorry` and `admit`; the exact-pin workflow invokes it before compilation. Regression fixtures are in `tests/test_lean_source_sanity.py`.

Validation boundary: scanner implementation passed CACE collaboration run `43469516682` and Lean Source Sanity run `43469517086` on `dca948e89c8153693b287da8c8c31caa84a568eb`. The corrected final multiline mutation fixtures are in `f66eaa63c5480bc49db2d377019087d4e1643475` and need a fresh exact-head run. Earlier collaboration run `43468823050` validated `1739266a2a22fde3c2fbae07f3ec232027cf07fb`, before this scanner extension. None of these is a Lean kernel compile or proof qualification.

Next: exact-head scanner/collaboration validation; then manually dispatch the exact-pin Lean standalone preflight for `CACEFormal.ContinuumSimplexCore` with Lean `v4.32.1` and Mathlib `520045ab14e26149ee970e2e617ca04b09bde5d6`. Keep the module quarantined until every formal and independent CACE gate passes. PR #102 remains stacked on PR #101; do not merge independently.

## 2026-11-13 production Merlin artifact-lineage continuation

Source implementation is being developed in [Expert Robot PR #144](https://github.com/Mannyspiro/expert-robot/pull/144), stacked on Expert Robot PR #143. Live source branch: `feat/merlin-artifact-version-lineage-20261113`; latest observed head: `7593b782d688132b206fc16f83ddf131b919a496`. PR #144 remains OPEN/DRAFT and unmerged.

The source branch extends the existing canonical `MerlinRegistry` with append-only per-project/per-logical-path artifact versions and strict `merlin-artifact-ref/1` identities. The reference binds project ID, normalized logical path, chronological version and SHA-256. Resolution re-hashes exact bytes and checks size; historical versions remain resolvable. Currentness is based on version identity, not digest equality, including the A -> B -> A reversion case.

Artifact references have been propagated source-side through:
- research evidence results, graph node metadata and graph-edge provenance (graph identity includes version);
- `merlin-research-task/2` dispatch envelopes;
- Hermes input context and `merlin-hermes-task-result/2` receipts;
- the production Hermes runtime's injected canonical registry resolver, which revalidates input/output references;
- Avrea dispatch receipts and exact-byte input transfer, capped at 25 MiB per artifact / 50 MiB aggregate;
- Avrea collected output receipts and durable outbox events.

The source branch adds regressions for historical versions/reversions, tampered blobs, Hermes reference validation, missing-validator fail-closed behavior, Avrea input resolution and exact-byte transfer. Exact current-head native CI run `43534991502` and unified platform run `43534991526` were pending/queued at the latest live check. Earlier native CI passed on prior commits but does not validate the latest head. Do not claim the unified suite passed until a completed success for the exact current head is observed.

Critical remaining boundary: CACE's actual signed EvidenceBundle contract has not yet been updated to include the complete artifact reference (especially chronological version) in its signed statement and independent verification. Source-side digest checks are not a substitute. The next coordinated change must update the CACE verifier/signer producer and Merlin adapter together, require exact reference equality, re-resolve the referenced bytes independently, and retain pinned trust verification. Until then, end-to-end CACE artifact-version verification is NOT COMPLETE.

PR #144 has not changed any runner host, IAM, credentials, signer keys, deployment, or production configuration. It grants no promotion authority. Keep PR #144 draft and stacked; do not merge it independently. Keep signing, verification and promotion as distinct transitions.


## 2026-11-14 production Merlin continuation

Read `docs/MERLIN_PRODUCTION_HANDOFF.md` for the full exact state. Live source recheck:
- Expert Robot PR #144 head `7593b782d688132b206fc16f83ddf131b919a496`, OPEN/DRAFT and stacked on #143.
- Exact-head native CI #43534991502: SUCCESS.
- Exact-head unified platform run #43534991526: CANCELLED. It is not a pass; inspect cancellation cause and obtain a fresh exact-head run.
- No merge, deployment, runner/IAM/credential change, signer setup or promotion.

CACE architecture clarification from current repository inspection:
- The generic Ed25519 statement supports signed `bindings`, but the current CLI sign path binds only qualified commit and proof-artifact digest.
- Generic signature verification validates the embedded key/signature but does not independently trust-pin the key.
- EvidenceBundle v1 is a digest/size/Merkle manifest; it does not independently resolve a Merlin project/path/version reference or fetch canonical registry bytes.
- The current OCI MCP server is an operational control plane, not a Merlin verifier/signer endpoint. The previously assumed `ops/oci_mcp/merlin_rsi_verifier.py` path is absent from current main; re-discover actual implementation paths before coding.

Next production gate: strict CACE request schema + independent canonical-registry byte resolution + full ArtifactRef binding in EvidenceBundle/signed statement + consumer trust-pin verification. Keep `proof_effect=none`. Do not claim end-to-end verification until the actual resolver, signer, pinned trust and Merlin response validation work together. Do not create/configure keys, secrets, endpoints, IAM or host services without separate authorization.
