# CACE Master Idea Roadmap and Dependency Timeline

Status: durable planning authority for implementation order.  
Date: 2026-09-19.  
Truth rule: this roadmap is **not proof evidence**. Formal truth remains controlled by Lean source, proof contracts, exact-head qualification, kernel/axiom audit, and provenance.

## 1. Purpose

This file consolidates meritorious CACE ideas recovered from:

- the durable chat-derived idea ledger;
- prior master timelines and remaining-plan files;
- proof-roadmap work;
- current GitHub branches/PRs;
- recent multi-user, multi-window, local-AI, Math Coin, science-object, and commercial-product discussions.

The objective is to make future coding agents able to answer three questions immediately:

1. **What must never be weakened?**
2. **What should be built next?**
3. **Where do speculative/research ideas belong without losing them?**

No idea is promoted to theorem/product truth merely because it appears here.

## 2. Non-negotiable architecture

Every future implementation must preserve:

1. Evidence classes remain distinct: experimental, numerical, exact/symbolic, interval/certified, formal, cross-verified.
2. AI agreement/confidence never equals proof.
3. Formal proof uses pinned/exact-head qualification, kernel/axiom audit, proof contracts, executable/source binding, and stale-evidence invalidation.
4. Scientific objects are typed: domain/codomain, shape, units, assumptions, provenance, verification state.
5. Browser/webapp is the only public application surface; privileged science/AI/wallet/proof/database/native services stay behind a hardened private boundary.
6. User/tenant state never changes scientific truth.
7. Layout/coordinate visualization never changes scientific meaning unless an explicit scientific transform node exists.
8. Economic/heartbeat/reward state never changes proof/evidence state.
9. Local AI is sandboxed before it exists, not afterward.
10. Unknown coding tasks use ranked alternatives, Build Lite, typed helper tools, bug-family sweeps, and regression guards rather than silently dropping features.
11. Proprietary CACE proof machinery, custom mathematical implementation, source structure, keys, prompts, and trade-secret internals stay out of customer help/telemetry.
12. Public help explains visible contracts, rigor, examples, and limitations without exposing under-the-hood proprietary methods.

## 3. Live frontier captured for this roadmap

### Formal proof

PR #42:
- branch: `proof/v3.41a-box-zero-boundary-core`
- exact head: `f13b63c02c74209f3e47a88ab11ed7b4a1e33c72`
- v3.41A ranks 1-8 implemented and audited-root preflight passed.
- canonical exact-current-head qualification remains the promotion gate before advancing the formal branch.

### Molecular/materials/physics

PR #48:
- branch: `feature/molecular-materials-physics`
- head: `a23a153f984f5dbb3b6827bef84e95a50c8fcaf4`
- includes typed molecular/protein/material/physics objects and AlphaFold DB API import path.

### Research controls / protein play

PR #50:
- branch: `feature/research-control-economy-open-problems`
- head: `5dedbb6e4b402656fc5aba9f0e4186bbcf2804f0`
- contains compute economy, capability gate, open-problem/protein play, heartbeat integration.

### Production-builder/account/network branch

PR #51:
- branch: `feature/network-account-agent-bootstrap`
- head: `c645c1941372f8317046dfa1ee4291553f8b66cc`
- broad Python regression currently has a narrow acceptance-gate defect:
  - missing `import re` in a repaired guardrail test;
  - the edited proof-sensitive bridge test triggered qualification-drift detection and must be handled without weakening the formal contract.
- substantive Python/C++ regression work otherwise reached the acceptance gate.

### Design branches

- `design/multi-window-spatial-routing`: semantic multi-window/non-Cartesian layout design.
- `design/local-hybrid-ai-sandbox`: Build Lite -> builder -> sandbox -> local hybrid AI sequence.
- `design/math-coin-user-approval`: Math Coin approval/custody/reward/proof-access design work; master roadmap preserves the intent even if branch work is incomplete.

## 4. Ranked implementation list

Ranking is dependency-first, not excitement-first.

### Rank 1 — Repair PR #51 regression without weakening qualification

Why first:
- production integration should not advance from a red exact head.

Required:
- add the missing regex import/guard regression correctly;
- restore or properly requalify proof-sensitive bridge-test identity rather than hiding qualification drift;
- rerun cheap guards;
- run one full Python/native regression on the repaired exact head;
- only then call the engineering head merge-quality.

### Rank 2 — Canonical qualification of the v3.41A formal head

Run the one clean canonical exact-current-head qualification for:
`f13b63c02c74209f3e47a88ab11ed7b4a1e33c72`

Capture:
- exact source SHA;
- qualified SHA;
- proof contract;
- axiom audit;
- theorem metadata;
- provenance;
- durable evidence.

Do not alter that head until evidence is captured.

### Rank 3 — Finish the v3.41 continuum boundary/proof sequence

Continue in dependency order:
- B: fixed-test-field normal-trace continuity, dense-core annihilation, smooth-to-graph map/core;
- C: H1-zero graph closure and functional zero-trace endpoint;
- D: pairwise trace cancellation -> orthogonality -> continuum Prager-Synge;
- E: fully concrete box H1-zero equilibrated endpoint.

Then consider:
- q-side zero-normal H(div) core;
- mixed boundary masks;
- polynomial bubble core;
- compact-support core;
- whole-space/bounded-domain H(div) density.

### Rank 4 — Freeze the proof constitution and proof/claim navigation surface

Complete:
- Proof Explorer;
- theorem/assumption dependency graph;
- exact theorem identity;
- claim registry;
- proof ledger;
- qualification-drift detection;
- executable/source theorem linkage;
- stale evidence handling.

This is the foundation every later science/product feature relies on.

### Rank 5 — Finish Build Lite + coding-agent reliability architecture

Required:
- deterministic changed-path task DAG;
- critical-path scheduling;
- content-addressed cache reuse;
- proof-sensitive cache = restore-only;
- unknown-feature 10-approach ranking;
- helper-tool fallback;
- root-cause -> sibling sweep -> regression -> permanent guard;
- deterministic AI navigation indexes.

### Rank 6 — Hardened browser/private-service deployment boundary

Production shape:
`Browser -> HTTPS/WSS gateway -> typed private IPC -> hardened local/private service plane`

Private:
- orchestrator;
- scientific runtime;
- C++/GPU workers;
- local AI;
- account/protein stores;
- network/economy/wallet brokers;
- durable evidence;
- isolated proof runner.

### Rank 7 — Multi-tenant account/instance foundation

Build:
- one durable logical instance per account;
- shared immutable reviewed release image;
- tenant-scoped storage, queues, cache, wallets, proteins, experiments;
- horizontal stateless gateway/API;
- warm/ephemeral isolated workers;
- fair scheduling, quotas, backpressure;
- suspend/resume/reconnect;
- no cross-tenant access by default.

### Rank 8 — Authentication, one-person trial, and non-destructive entitlement system

Preserve:
- no-card free trial;
- one trial per verified person identity anchor;
- account deletion/recreation does not reset trial;
- recovery/merge path;
- post-trial view/export/delete/recovery/help access;
- no destructive/ransomware-like expiry behavior.

### Rank 9 — Save/replay/provenance/export and durable evidence storage

Ship:
- versioned `.cace`;
- immutable snapshots;
- canonical JSON;
- semantic/full hashes;
- autosave/recovery;
- replay;
- evidence bundles;
- printable/exportable reports;
- provider-independent host journal/evidence directory;
- OCI/object-storage mirror option;
- content-addressed manifests.

### Rank 10 — Full typed browser Studio parity

The browser must become the real scientific playground:
- drag/drop;
- click-to-connect typed/unit-aware ports;
- forms;
- minimap;
- grouping/subgraphs;
- scoped async run;
- cancel/pause/resume where supported;
- evidence/proof indicators;
- shared semantics with desktop/CLI/agent.

### Rank 11 — Complete customer-safe Help system

Generate help from the live registry:
- every customer feature;
- every registered module;
- 2+ direct examples per module;
- 2+ combined-module examples;
- visible inputs/outputs/parameters/types/units;
- evidence/rigor guidance;
- no proprietary algorithms/custom internal math/theorem bodies/source internals/hidden defaults.

### Rank 12 — Multi-window + multi-monitor semantic routing

Implement in order:
1. typed WindowIntent/WindowPlacement;
2. stable rectangular Cartesian router;
3. user pin/lock + persistence;
4. hex axial/cube semantic routing;
5. radial/polar focus-context;
6. monitor remapping;
7. hyperbolic hierarchy;
8. Voronoi/power dashboard;
9. Hilbert/Morton addressing;
10. simplex/complex/fractal/3D plugins.

Invariant: OS/browser windows remain ordinary rectangles; non-Cartesian geometry is semantic presentation.

### Rank 13 — Coordinate-system and 2D/3D visualization palette

Preserve:
- Cartesian;
- triangular;
- hexagonal;
- Einstein/aperiodic;
- alternate complex/root-of-unity bases;
- recursive/fractal views;
- 2D/3D toggle;
- orbit/zoom/pan/reset/gizmo;
- visualization-only unless an explicit semantic transform is present.

### Rank 14 — Research notebook and Build-on-Canvas workflow

Implement:
- Research Idea object;
- Idea -> Testable -> Experimented -> Promising -> Proof Candidate;
- Keep / Useful / Reject;
- hypotheses/notes/modules/evidence/provenance;
- Proposed Experiment preview;
- Minimal / Balanced / Exploratory graph proposals;
- Build on Canvas only after user approval.

### Rank 15 — Sandbox-first local hybrid AI foundation

Hard order:
`Build Lite -> builder/bug-sweep -> sandbox -> local hybrid AI -> curriculum -> canvas/heartbeat`

Hybrid components:
- compact local LLM;
- typed operator planner;
- math/science tool router;
- provenance-aware local retrieval;
- specialist models;
- independent checker layer;
- curriculum teacher;
- heartbeat scheduler;
- optional one-way observers.

Default AI capabilities:
- network off;
- shell off;
- self-modification off;
- package installation off;
- proof/evidence write forbidden;
- wallet keys/secrets forbidden;
- bounded resources.

### Rank 16 — Reasoning-first AI curriculum

Prioritize:
- typed operator programs;
- Paired Intervention Consistency;
- irrelevant-perturbation invariance;
- procedural task generation;
- held-out composition;
- relabel/symmetry/coordinate transfer;
- inverse problems;
- external executable checking;
- operator memory with preconditions/invariants/inverses/cost/failure domains.

External/public methodology ideas may inspire independent work only with verified IP/license provenance.

### Rank 17 — Conway-inspired heartbeat and research-attention field

States:
DORMANT, READY, ACTIVE, WAITING, BLOCKED, STALE, VERIFYING, VERIFIED, FAILED, RESEARCH_INTEREST.

Rules:
- deterministic;
- dependency-aware;
- semantic-hash changes propagate stale;
- AI attention can never set VERIFIED/PASS;
- heartbeat deltas can guide AI/context efficiently.

### Rank 18 — Grow / stochastic discovery engine

Preserve:
- seeded random walks;
- combinatorial/group constructions;
- optional growth operator `G_t`;
- rotation/isometry operators;
- chaos injection;
- deterministic seed/hash replay;
- animated transformations;
- Keep/Useful/Reject integration.

Research only until semantics/invariants are explicit.

### Rank 19 — Deterministic addressing, serialization, and safe parallelism

Develop:
- Cantor/Hilbert-hotel-inspired injective tuple addresses;
- address -> resource class -> deterministic queue slot -> execution -> content hash -> ledger;
- fair scheduling/starvation/cancellation handled separately;
- serialization plan for safe parallel independent work;
- proof-job collision avoidance.

### Rank 20 — Molecular/protein/material/physics integration

Integrate PR #48 then PR #50 on a common base:
- Atom/Bond/Molecule;
- safe home-lab chemistry;
- ProteinSequence/Structure;
- AlphaFold DB API import with attribution;
- Protein Playground/heartbeat;
- coarse deterministic fold search with explicit non-global-minimum claim;
- MaterialCandidate;
- established-vs-theoretical PhysicsCanvasObject;
- open-problem cards/play.

### Rank 21 — Protein library/account scientific storage

Account opt-in:
- persistent protein objects;
- source/license/attribution;
- semantic hashes;
- no persistence if consent disabled;
- tenant isolation;
- no clinical/experimental overclaim.

### Rank 22 — Core certified FEM/PDE production expansion

Preserve and extend:
- exact P1/RT0 certificate engine;
- affine/Piola transport;
- arbitrary-mesh equilibration;
- RT1 higher-order equilibrated flux;
- production P2;
- DWR;
- heterogeneous/data-oscillation bounds;
- adaptivity integration.

### Rank 23 — Mixed, spectral, parabolic, Maxwell/Stokes production tracks

Develop:
- mixed/saddle-point/Brezzi infrastructure;
- verified eigenvalue inclusion/counting;
- sparse interval eigensolver;
- parabolic/time-dependent certification;
- FEEC/Nedelec/Maxwell-compatible complexes;
- Stokes mesh-family production.

### Rank 24 — DG/SUPG/elasticity/contact/Helmholtz/nonlinear PDE tracks

Only promote as typed modules with explicit evidence ceilings:
- DG;
- SUPG;
- elasticity;
- contact;
- Helmholtz;
- nonlinear PDE validation;
- production solver/error-estimator pairing.

### Rank 25 — Geometric algebra + sparse graded computation

Preserve:
- Clifford/PGA/CGA foundations;
- vectors, bivectors, rotors, spinors, blades, k-cells;
- sparse graded representations;
- translate combinatorial groups/structures into geometric objects where benchmarks show benefit;
- state invariants, reversibility/loss, and performance.

### Rank 26 — Certified coordinate research

Research:
- multiscale shear tiles;
- truncation/tail bounds;
- Hilbert finite-prefix coordinates;
- product mosaics;
- adaptive dimension selection;
- curved/sheared cells;
- coupled shears;
- complex/Eisenstein bases;
- fractal coordinate systems.

These must not be marketed as mathematical breakthroughs until independently established.

### Rank 27 — Custom formal library / smaller dependency footprint research

Goal:
- reusable custom CACE Lean modules for stable identities/combinations;
- potentially smaller/self-owned formal layers only where rigor/licensing remain intact;
- never replace the trusted proof kernel with an unqualified shortcut.

### Rank 28 — Broader scientific module migration

Candidate typed modules:
- statistics;
- ODEs;
- optimization;
- signal/sensor;
- geometry/robotics;
- biology/chemistry geometry;
- topology/high-dimensional coordinates;
- arbitrary precision;
- self-similarity.

Migrate only with assumptions, reproducibility, evidence class, and real tests.

### Rank 29 — Quantum research modules

Preserve as research:
- QAOA;
- boson sampling/loss;
- spin systems;
- classical-vs-quantum benchmark examples.

Never imply supremacy or theorem proof from benchmark success.

### Rank 30 — Directional local-AI networking

Default network OFF.

When enabled:
- separate Receive code;
- separate Outgoing code;
- short-lived/single-use/hash-stored;
- source-outgoing + target-receive creates one directed link;
- reverse direction requires separate pairing;
- narrow economy/heartbeat capability only;
- no shell/filesystem/proof/evidence/wallet-key/model-control authority.

### Rank 31 — Public multi-user service

Provide one owned HTTPS signup/recovery URL.

Production policy:
- eligible user -> durable tenant instance;
- requested CN/KP access policy enforced at trusted edge and sensitive routes;
- country policy remains separate from sanctions/export/end-use compliance;
- local agents connect outbound; users need not expose inbound router ports.

### Rank 32 — Privacy-preserving telemetry and improvement loop

Three lanes:
1. essential operational heartbeat;
2. privacy-controlled aggregate/pseudonymous product analytics;
3. actual proof/research contribution explicit opt-in.

Essential telemetry may include:
- version;
- health;
- resource/queue buckets;
- job/error counts;
- proof-status counts.

Never essential telemetry:
- theorem/proof text;
- equations;
- AI conversations;
- protein content;
- filenames;
- precise location;
- wallet secrets.

### Rank 33 — Internal compute-credit economy

Before real assets:
- spare CPU/GPU headroom;
- internal non-monetary credits;
- bounded task bids;
- host-measured outcomes;
- strategy performance from external useful work;
- economy cannot alter proof truth.

### Rank 34 — Math Coin simulation and user-approval layer

Constitution:
- fixed 500,000,000,000 MATH;
- no mining;
- vault + circulating + escrow + burned conservation;
- decade unlock tranches are explicit constitutional policy;
- burn-to-compute only after measured settlement;
- internal credits never convertible into MATH.

User-spend design:
- AI may request but never approve;
- user sees amount, purpose, provider/action, fees, before/after balance;
- approve once/reject;
- optional separately configured bounded budget;
- introductory reference: 1,000 MATH = USD 0.01;
- Help -> Math Coin -> Buy More;
- no live payment rail until security/compliance/fraud/tax review.

Master custody:
- recovery/private material never Git/browser/AI/log/email;
- owner email may receive secure-retrieval-ready notification only.

### Rank 35 — Contribution rewards and tiered proof access

Basic:
- opt-in selected discoveries;
- host-reviewed impact score;
- proportional MATH transfer from reward treasury;
- no new minting;
- dedupe/sybil controls;
- user/AI cannot self-award.

Researcher:
- customer-safe own-instance LaTeX proof/result views;
- assumptions;
- attribution;
- evidence/qualification;
- provenance/certificate IDs;
- limitations;
- no proprietary theorem source/proof search/internal computation trace.

Enterprise/Government:
- Request Full-Rigor Proof Package;
- prove first, sell second;
- proof-ready gate before payment;
- customer deliverable excludes CACE Background IP unless separately contracted.

### Rank 36 — High-capability AI admission gate

Default OFF.

If enabled:
- only admits the declared provider capability tier;
- does not grant network, shell, self-modification, worker spawn, plugin install, proof/evidence mutation, wallet keys, or unbounded compute.

### Rank 37 — One-way latent observers

For instrumentable local/open models only:
- copy hidden-layer matrices through host broker;
- multiple immutable observer containers;
- full/sketch/hash modes;
- observer channel is one-way;
- inference receives no feedback/control channel.

### Rank 38 — Source secrecy and customer-facing proof disclosure controls

Maintain:
- private theorem source;
- opaque stable certificate IDs;
- customer-specific readable derivation;
- no proprietary reusable theorem bodies/proof strategies;
- controlled LaTeX/PDF rendering;
- trade-secret disclosure review;
- signed artifact/manifests.

### Rank 39 — Enterprise account/compute/commercial polish

Account tiers:
- Basic;
- Researcher;
- Enterprise.

Preserve tiered compute controls and audited entitlements.

Do not let commercial rights/accelerators affect theorem truth.

### Rank 40 — Long-horizon adaptive/novel research

Keep in research backlog until explicit semantics/tests exist:
- adaptive/deformed Conway architectures;
- scientific/neural compiled exports;
- generally-useful research mode;
- infinite/fractal coordinate experiments;
- novel product mosaics;
- random-walk/growth/rotation systems;
- experimental 3D/XR workspace;
- advanced combinatorial transforms.

## 5. Dependency timeline

This is a build-order timeline, not a calendar promise.

### Phase A — Red-to-green and truth baseline
Exit only when:
- PR #51 exact head is regression-green;
- qualification drift is resolved correctly;
- v3.41A canonical qualification is captured;
- proof constitution is not weakened.

Tracks: 1-4.

### Phase B — Builder/reliability foundation
Exit only when:
- Build Lite is trusted for coordination;
- bug-sweep architecture works;
- deterministic indexes exist;
- evidence/log persistence is durable.

Tracks: 5, 9.

### Phase C — Production service foundation
Exit only when:
- browser-only gateway is enforced;
- multi-tenant tenant isolation exists;
- account/trial/auth is server-side;
- private-service sandbox policy passes negative tests.

Tracks: 6-8.

### Phase D — Complete scientific UX shell
Exit only when:
- full browser canvas works;
- save/replay/export works;
- help coverage is complete;
- multi-window base router works;
- 2D/3D/coordinate palette preserves semantics.

Tracks: 10-13.

### Phase E — Research workflow
Exit only when:
- Research Idea lifecycle works;
- Build-on-Canvas preview works;
- proposal strategies work;
- proof/evidence status is visible.

Track: 14.

### Phase F — Local AI foundation
Exit only when:
- sandbox exists first;
- hybrid AI operates locally/offline;
- typed tool planner/checker separation works;
- paired intervention/invariance evaluations pass.

Tracks: 15-16.

### Phase G — Heartbeat/Grow/distributed research coordination
Exit only when:
- heartbeat is deterministic/non-evidentiary;
- Grow is reproducible;
- addressing/serialization is collision-safe;
- AI attention stays outside proof authority.

Tracks: 17-19.

### Phase H — Scientific domain integration
Exit only when:
- PR #48/#50 integrated on a common base;
- protein/material/physics/open-problem modules are typed;
- no evidence overclaims;
- account protein storage honors consent.

Tracks: 20-21.

### Phase I — Certified PDE/scientific expansion
Progress in mathematical dependency order:
- RT1/P2/DWR/robust bounds/adaptivity;
- mixed/spectral/parabolic/Maxwell/Stokes;
- DG/SUPG/elasticity/contact/Helmholtz/nonlinear.

Tracks: 22-24.

### Phase J — Advanced mathematical/coordinate research
Research and benchmark before promotion:
- geometric algebra;
- combinatorial transforms;
- certified exotic coordinates;
- custom formal-library experiments;
- quantum/broader science modules.

Tracks: 25-29.

### Phase K — Networked service/economy
Only after account/sandbox/multi-tenant boundaries are real:
- directional AI networking;
- public service;
- telemetry;
- internal credit economy.

Tracks: 30-33.

### Phase L — Math Coin / rewards / proof commerce
Simulation first.

Only after security/compliance/custody review:
- user approval;
- buy-more flow;
- master custody;
- contribution rewards;
- researcher proof view;
- enterprise proof commerce.

Tracks: 34-35, 38-39.

### Phase M — High-capability/observer research
Only after the local AI/sandbox is mature:
- high-capability gate;
- one-way latent observers.

Tracks: 36-37.

### Phase N — Long-horizon experimental research
No production promotion without independent validation.

Track: 40.

## 6. Complete recovered idea families

The append-only detailed inventory remains:
`docs/CHAT_IDEA_LEDGER.md`

The roadmap intentionally does not rewrite every I-entry in full. It preserves them by family:

- I001-I005: evidence/proof/reliability/agent collaboration.
- I006-I015: local AI, Grow, notebook, safety, model ecosystem.
- I016-I024: tilings, complex/fractal, 3D, multiscale/Hilbert/shear coordinates.
- I025-I030: geometric algebra, combinatorial geometry, custom formal modules, exact transforms, discrete and continuum PDE.
- I031-I037: theorem batching, H1-zero, q-side, mixed boundaries, bubbles, compact support, H(div) density.
- I038-I043: stochastic transforms, Cantor addressing, deterministic scheduling, serialization, caches, durable evidence.
- I044-I055: browser Studio, collaboration, save/export, AI navigation, legacy domains, quantum/broader science, adaptive Conway, scientific/neural export, view-vs-semantic rotation, generally-useful mode, continuity.
- I056-I060: reasoning pedagogy, paired intervention, geometric reasoning, operator memory, heartbeat.
- I061-I066: molecules, protein folding/import/play, materials, physics, open problems.
- I067-I071: heartbeat economy, high-capability gate, latent observers, Math Coin, AlphaFold DB API.
- I072-I078: code-builder fallback, directional AI pairing, browser-only gateway, complete help, one-person trial, multi-tenant service, privacy-preserving public signup/telemetry.
- I079: semantic multi-window/non-Cartesian routing.
- I080: sandbox-first local hybrid AI.
- I081: human-approved Math Coin spend/buy-more/master custody.
- I082: Basic contribution rewards + Researcher LaTeX proof view + Enterprise/Government proof commerce.
- I083: this master roadmap/implementation timeline as durable AI navigation.

## 7. Historical numerical/scientific roadmap retained

Older CACE roadmaps contain useful tracks that remain valid as research/engineering goals:

1. RT1/higher-order equilibrated flux.
2. Production global P2.
3. PDE-level goal-oriented DWR.
4. Robust heterogeneous/data-oscillation guarantees.
5. Adaptivity theorem integration.
6. Mixed/saddle-point methods.
7. Verified spectral bounds.
8. Parabolic/time-dependent certification.
9. FEEC/Maxwell-compatible complexes.
10. Integrated evidence architecture.

They remain subject to the current stronger evidence/proof constitution.

## 8. Rules for future coding agents

Before substantial work:

1. Read `AGENTS.md`.
2. Read `CACE_AGENT_BOOTSTRAP.json`.
3. Read `CACE_CODE_BUILDER_BOOTSTRAP.json`.
4. Read this roadmap.
5. Read `docs/CHAT_IDEA_LEDGER.md`.
6. Read `docs/GOAL_REGISTRY.json`.
7. Refresh live GitHub PR/Actions state.
8. Run Build Lite.
9. Work on the highest-ranked unblocked item compatible with the current branch.
10. Never mix proof-sensitive and unrelated feature work merely to save a commit.
11. New meritorious ideas are appended, deduplicated, linked to goals, and ranked by dependency.
12. Side-branch design work remains design until integrated and tested.
13. Never claim production grade, formal proof, or legal/compliance readiness without the relevant real gate.

## 9. Priority scoring rule for new ideas

Rank new ideas using:

1. closes a correctness/proof/security gap;
2. dependency leverage;
3. architecture preservation;
4. user/product value;
5. testability;
6. reuse of existing CACE modules;
7. implementation tractability;
8. compute/CI cost;
9. maintainability;
10. research novelty/option value.

Proof/security correctness always outranks novelty or UI polish.

## 10. Do-not-lose research shelf

These concepts have merit but are intentionally not top-of-line production work:

- Cantor infinities/infinite collections as coordinate research;
- complex bases such as i / omega-root systems;
- fractal coordinate representations;
- certified truncation tails;
- arbitrary tilings in high dimensions/non-Euclidean settings;
- rotor/spinor/k-cell neural representations;
- random-walk/exponential-growth/rotation experiments;
- adaptive Conway research;
- boson-sampling/QAOA/spin-glass examples;
- compiled scientific/neural environments;
- local hidden-layer observer research;
- VR/XR spherical workspaces.

Keep them in the ledger and research modules; do not delete them merely because they are deferred.
