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

## Merlin fixed process-recovery validation — November 21, 2026

The explicitly authorized code-only transfer and fixed validation completed in [run 44899455087, attempt 1](https://github.com/morganaspim/Cace-app/actions/runs/44899455087), workflow commit `4ef0d6add206ba2d0cbd25eadcbc5f3c609a0f58`. The selected Merlin source is `Mannyspiro/expert-robot@4847d90dca4266d42651a8b9538c3eeae8a423b1`.

All **386 software tests, eight kernel cases and six context cases passed** on `cace-oci-a1` (ARM64, Python 3.9.25). The downloaded artifact matched GitHub artifact `14704988710`, 529,239 bytes, SHA-256 `fbc803cef0c097bb8b43cdf2f3991d72b37c5a0ab80b3639e539130ead25457f`. Two same-team artifact reviews checked all 117 source files, actual test starts/stops, exact named cases, source/controller/loader identities and raw process receipts.

Completed-process recovery recorded one original process launch, blocked ordinary retry, performed checker-only recovery, and returned the same recovered receipt on fresh-worker replay without relaunch. The monitored service fields remained active/running/enabled with MainPID 2507219 before and after the run; these fields are a bounded observation, not a comprehensive service audit.

The exact checkpoint is `ops/merlin_dot/validation-results/process-recovery-20261121.json`. Critical runtime evidence is retained outside GitHub in an evidence-only archive (SHA-256 `81ef33bdfc7522646161d15249b88d34ee6064c34890814e9e45f2be43eb9cdd`); repository-backed source/controller copies remain in their repositories. No corrective native rerun was needed.

This is Class B Merlin engineering acceptance of the declared fixed synthetic selection. It does not qualify CACE's scientific core, establish actual native model review or model quality, authorize merge/deployment, or complete Merlin's production plan. Production service configuration, permissions and private runtime state were not changed. Subsequent weight-binding or evidence-admission code requires its own source-specific validation.

## Merlin weight-binding and evidence-admission validation — November 21, 2026

The subsequent implementation candidate `Mannyspiro/expert-robot@01016e832f763c76744e404041355b33d15fb621` now has its own source-specific native result: [run 44901033194, attempt 1](https://github.com/morganaspim/Cace-app/actions/runs/44901033194), workflow commit `3ff164611e3fed46a3cbd3a23602a32bd2c219ff`. [Draft PR186](https://github.com/Mannyspiro/expert-robot/pull/186) contains optional host-authenticated coder-A weight invocation binding and v3 native build-evidence admission.

All **473 software tests, eight kernel cases and six context cases passed** on `cace-oci-a1` (ARM64/Python 3.9.25). The 121 selected source files and all 473 distinct start/stop pairs matched their frozen identities. The native software run measured 145.802 seconds. Artifact `14706041876` is 576,733 bytes with SHA-256 `ab1eb1b425a64ce2154c9a8e24ea05753084539bf8e79da0ec22c6bd921184fe`. The same 473 tests also passed locally; this is not a controlled cross-machine performance comparison.

Two same-team artifact reviews accepted the retained evidence within its recorded scope. Process, checker-result and recovery bodies were rehashed; other linked bodies were not independently re-resolved. Recovery again recorded one original process launch, blocked ordinary retry and completed checker-only recovery with exact fresh-worker replay. The four monitored service properties remained unchanged. No corrective native rerun was required.

Read-only pure admission validators passed against the actual downloaded native artifact and provider metadata. The tested source commit and later observed documentation/evidence publication head `04523cf629edf8c21056576dd227dea9ea0ba189` remain separate, with all 121 selected source blobs identical. This is no whole-commit or ancestry claim. No real native evidence was admitted using fixture authentication, and no production registry or live service was modified.

The narrow checkpoint is `ops/merlin_dot/validation-results/weight-binding-admission-20261121.json`. Critical runtime evidence is retained outside GitHub in `Merlin_production_candidate_validation_20261121.zip` (276,966 bytes; SHA-256 `6aa02f3437a7cff12f023d8d4a77daf10affebbd9de741ed67c129ebe12dbd74`). Repository-backed source/controller/loader and rejected-patch copies remain in Git. Exact rejected component versions were recovered, matched prior hashes and retained as reverse patches in PR186.

This remains Class B fixed synthetic Merlin engineering acceptance. Actual host authentication/custody, verified editable-model runtime, model efficacy and full-platform release gates remain open. No weights were loaded or edited, no model-quality gain or native model review was measured, no scientific core was qualified, and no merge/deployment occurred. The next weight-space experiment requires a permitted target/runtime, a representative baseline and independent oracle, frozen holdout evaluation and enforced resource limits.
