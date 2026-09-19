# CACE Master Build Specification

Status: authoritative implementation-intent and acceptance-criteria document for CACE Studio. It is **not** proof evidence, qualification evidence, or a claim that every item is implemented. Current implementation/qualification state lives in `docs/STATUS.md`; mathematical claim truth lives in the claim registry, proof ledger, formal sources, and exact workflow artifacts.

This document consolidates durable goals that have repeatedly survived design review across CACE development conversations. Future agents should update this document and `docs/GOAL_REGISTRY.json` when a new user goal has clear merit, while preserving the evidence rules below.

## 1. Product mission

CACE Studio is a rigorous scientific and mathematical workbench where a user can visually construct experiments from typed modules, execute them reproducibly, inspect assumptions and evidence, attach formal or certified results where justified, save/replay/export work, and optionally use local AI to propose or explain experiments.

The target product is a **working browser-accessible web application** with the same scientific semantics as the desktop/headless core. A user should be able to open a URL on another computer and use the visual scientific playground without writing code.

CACE must remain useful when AI is disabled, when GPU acceleration is unavailable, and when no external cloud service is reachable.

## 2. Authority hierarchy

When documents disagree, use this order:

1. exact source at the checked-out commit;
2. `cace_studio/data/claim_registry.json` and `cace_studio/data/proof_ledger.json` for promoted formal claims;
3. exact qualification artifacts for the commit being discussed;
4. `docs/CONSTITUTION.md`, `docs/CLAIMS.md`, `docs/ARCHITECTURE.md`;
5. `docs/STATUS.md` for current development state;
6. this file and `docs/GOAL_REGISTRY.json` for intended product direction;
7. historical release notes, demos, and archived plans.

Never use this specification to infer that an unfinished feature or theorem is complete.

## 3. Non-negotiable truth and evidence rules

CACE must keep the following evidence categories distinct:

- formal/kernel-checked theorem evidence;
- interval-certified evidence;
- exact/symbolic certificates;
- numerically verified evidence;
- engineering verification;
- empirical/benchmark evidence;
- conditional results;
- research/heuristic output;
- unknown, stale, failed, or not-run states.

A successful numerical run, GPU/CPU agreement, benchmark, hash, signature, AI answer, or provenance record is never silently promoted to mathematical proof.

`FAIL`, `NOT_RUN`, stale evidence, skipped verification, absent verification, and unresolved hypotheses must remain visible.

A theorem with hypotheses must retain those hypotheses everywhere: source, metadata, UI, reports, API output, examples, and documentation.

## 4. Formal-proof architecture requirements

Formal qualification remains fail-closed.

Required properties:

- pinned Lean toolchain and pinned Mathlib commit;
- exact-current-head checkout and clean-tree check;
- permanent proof guardrails and exact root-import allowlist;
- quarantine-before-promotion for new formal modules;
- explicit unfinished-token rejection;
- proof-plan/source content addressing;
- conservative reverse-dependent recompilation;
- audited root compilation;
- Lean.Environment theorem metadata generated from the loaded environment;
- kernel axiom audit with a narrow explicit allowlist;
- exact proof-contract endpoint equality;
- source/contract/executable binding;
- content-addressed exact-head attestation;
- independent artifact-integrity verification;
- qualification-drift detection after later commits;
- caches used only as acceleration, never as inherited proof;
- negative/fault-injection tests that may not be weakened to preserve desired status.

The project should prefer one deliberate expensive qualification run at a time. Safe cached toolchains, dependency trees, and build artifacts should minimize repeated downloads and compilation while preserving fresh exact-head evidence.

## 5. Target browser application

The web application is not a thin demo. It should expose the useful CACE Studio workflow through the browser.

### 5.1 Main workspace

Required workspace capabilities:

- searchable module library;
- drag modules onto the canvas;
- click-to-connect typed ports;
- visible incompatible-connection feedback;
- parameter/property forms with validation;
- multi-select, move, delete, copy/paste;
- undo/redo;
- alignment and organization tools;
- groups/subgraphs;
- minimap;
- zoom, pan, fit-to-selection, fit-all;
- deterministic graph serialization;
- autosave and crash/session recovery;
- explicit stale-evidence invalidation after semantic edits;
- selected-node plus upstream execution;
- full-graph execution;
- cooperative pause/resume/cancel;
- run progress/heartbeats;
- proof/evidence badges that reflect executed evidence only.

### 5.2 Scientific inspection

A user should be able to inspect:

- module inputs/outputs and units;
- assumptions and preconditions;
- generated proof obligations;
- current verification state;
- certificates and evidence artifacts;
- formal theorem dependencies;
- provenance and exact source/commit binding;
- numerical diagnostics and convergence information;
- CPU/GPU backend actually used;
- failure causes rather than generic red status.

### 5.3 Visualization, reports, save/export/print

The web app should support:

- useful charts/plots tied to actual experiment data;
- geometry/mesh visualization when relevant;
- proof/evidence graph views;
- readable canonical JSON;
- save/load of versioned `.cace` experiments;
- deterministic replay where possible;
- export of reports, evidence bundles, and data;
- print-friendly reports;
- clear distinction between a visual demonstration and a verified scientific result.

### 5.4 Coordinate-system and tiling visualization layer

CACE should let users change the **visual coordinate system** independently of the mathematical experiment. A coordinate view is presentation metadata unless an explicit computational transform module is inserted into the graph.

Core rule:

`canonical mathematical data -> view transform -> renderer`

Changing only the view must not alter theorem hypotheses, numerical inputs, certificates, verification state, or the semantic experiment fingerprint. Presentation/view state should have its own fingerprint. If a transform, quantization, snapping rule, or basis change is intended to alter computation, it must become an explicit typed semantic operation and therefore invalidate/recompute dependent evidence normally.

The GUI should provide a coordinate-view palette that can grow beyond conventional Cartesian axes. Useful views include:

- ordinary 2D Cartesian square grid;
- rotated/scaled Cartesian bases;
- polar views;
- triangular lattice coordinates;
- hexagonal tiling with axial/cube-style labels;
- barycentric/simplex views;
- user-defined lattice bases;
- Gaussian-integer style square lattice using a basis involving `1` and `i`;
- Eisenstein-integer style triangular/hexagonal lattice using `1` and `omega`, with `omega = exp(2*pi*i/3)`;
- experimental complex-radix views involving bases such as `i` or `omega`;
- periodic tilings by squares, triangles, hexagons, and other supported polygons;
- aperiodic/substitution tilings, including aperiodic monotile ("einstein") style views;
- hierarchical/fractal views such as quadtree, hex-tree, recursive substitution tilings, and tile-address coordinate systems;
- user-defined tiling/basis plugins that satisfy the same renderer contract.

A tiled or fractal coordinate view may label a location by both a canonical coordinate and a hierarchical tile address such as:

`level -> parent tile -> child tile -> local coordinate`

This makes recursive/fractal navigation possible without replacing the underlying mathematical coordinates.

The GUI should expose:

- coordinate-view selector;
- basis vectors / fundamental-domain overlay;
- grid or tile layer;
- axes and labels;
- nesting/substitution depth for hierarchical views;
- optional tile-address display;
- pan/zoom/fit behavior that is stable across view changes;
- side-by-side or overlay comparison of two coordinate views;
- export/import of presentation settings without changing scientific evidence;
- a clear badge stating `VISUALIZATION ONLY` for non-semantic coordinate views.

Novel tiled/fractal coordinate systems are encouraged as research features, but each renderer should define its mapping to/from canonical coordinates, ambiguity/non-invertibility behavior, numerical stability, and performance limits. Visual novelty alone must never be described as new mathematics or as proof.

### 5.5 Interactive 3D visualization mode

The GUI should provide an obvious **2D / 3D** view control for compatible scientific and coordinate visualizations.

3D mode is a presentation layer unless a semantic 3D transform module is explicitly inserted into the experiment graph.

Required interaction:

- click/touch and drag to orbit the view left/right and up/down;
- mouse wheel / pinch to zoom;
- pan control;
- reset/home camera button;
- fit-to-object / fit-to-data;
- optional axis-lock and top/front/side/isometric presets;
- visible orientation axes or orientation gizmo;
- keyboard/button alternatives for rotate left/right/up/down so 3D inspection does not require dragging;
- touch-friendly interaction on supported devices;
- preserve the selected coordinate/tile visualization while entering or leaving 3D when a compatible 3D embedding exists.

The renderer should preserve a canonical camera/view-state object separate from scientific state. Camera rotation, zoom, pan, perspective/orthographic choice, lighting, and view presets must not change theorem hypotheses, numerical inputs, certificates, verification state, or the semantic experiment fingerprint.

Coordinate and tiling views may optionally define a 3D embedding or extrusion, for example:

- Cartesian XY grid -> XYZ grid or extruded surface;
- triangular/hexagonal tilings -> planar 3D sheet, height field, or layered lattice;
- hierarchical/fractal tilings -> nested or stacked 3D visualization;
- proof/evidence dependency graphs -> optional spatial graph view;
- meshes, fields, surfaces, vector fields, and PDE data -> native 3D scientific rendering where appropriate.

A 3D embedding used only for display must be clearly labeled **VISUALIZATION ONLY**. If geometry is altered for computation, the alteration must be represented as an explicit typed semantic operation and dependent evidence must be recomputed.

## 6. Shared semantics across desktop, web, CLI, and agents

Desktop Studio, web UI, headless CLI, tests, and external agents must consume the **same core graph/module/evidence contracts**. No UI is allowed to invent a parallel scientific truth model.

The browser may use a service API, but core semantics belong in the canonical Python/C++/Lean layers.

Preferred shape:

`browser UI -> API/session layer -> canonical Python orchestration -> C++ kernels where justified`

with a parallel formal/evidence path:

`formal sources -> pinned Lean -> theorem metadata/kernel audit -> proof contract -> attestation -> canonical claim gate`

## 7. Research notebook and Grow workflow

CACE should preserve useful discoveries instead of losing them in transient chat.

A **Research Idea** object should support:

- editable title;
- notes;
- hypotheses;
- proposed experiment;
- associated modules;
- evidence links;
- provenance/source;
- status.

Canonical progression:

`Idea -> Testable -> Experimented -> Promising -> Proof Candidate`

A Research Idea must never become a Proof Candidate merely because an AI says it is true; the status represents workflow maturity, not proof.

### 7.1 Proposed Experiment -> Build on Canvas

For a Research Idea, CACE should be able to propose a small module graph, show the graph before mutation, and add it to the scientific canvas only after user approval.

Three proposal strategies are required:

- **Minimal** — lowest reasonable compute and smallest graph;
- **Balanced** — best-connected practical graph;
- **Exploratory** — a slightly more creative Grow-influenced graph while keeping assumptions explicit.

The preview should show modules, edges, parameters, assumptions, expected outputs, evidence class, compute estimate, and why each node is present.

## 8. Optional local AI / GenAI architecture

AI is a research assistant, not a verifier.

### 8.1 User experience

Users should be able to select and configure a supported local AI provider from the GUI with no coding. AI must have an obvious OFF state.

Supported interaction goals include:

- explain a module, theorem, certificate, or failure;
- answer how to perform a scientific experiment;
- explain rigor/evidence status;
- suggest experiments;
- propose small canvas graphs;
- build demo drafts;
- help interpret results;
- suggest next tests or proof obligations;
- maintain heartbeats/status during longer local tasks.

Existing modes such as OFF / Hints / Teacher / Researcher / Autonomous should remain explicit policy modes, not hidden behavior.

### 8.2 Local hybrid model goal

A longer-term local AI may combine:

- a local LLM for language/reasoning;
- a computationally inexpensive neural component;
- CACE-discovered mathematical transforms/features where they are demonstrated to improve cost or quality;
- retrieval over local project/module/proof metadata.

Efficiency gains discovered by CACE may improve the model, but only after measurable validation.

### 8.3 Zero-contact sandbox

The strongest local-autonomy mode should support a **zero-contact architecture**:

- no Internet access from the model sandbox;
- no cloud credentials;
- no arbitrary host filesystem access;
- no direct shell/network control;
- capability-mediated access only to approved experiment/module APIs;
- bounded resource limits;
- explicit import/export boundary;
- auditable action log;
- human approval for consequential canvas/source mutations.

This sandbox boundary should be designed so that even a highly capable local model cannot silently escape into network/cloud control.

AI-generated statements never become evidence merely because they were generated inside the sandbox.

## 9. Python, C++, GPU, and numerical architecture

Python is the orchestration/research integration layer.

C++20 is for expensive, justified kernels such as sparse algebra, FFT-like transforms, geometry/mesh operations, PDE kernels, interval kernels, and other performance-sensitive work. Use pybind11 or another explicit stable boundary.

GPU use must be optional. Every GPU-capable run should report the actual backend and any fallback. CPU/GPU agreement may be cross-backend evidence but is not proof.

Performance work should favor:

- deterministic fingerprints;
- content-addressed caches;
- sparse representations;
- streaming/chunked algorithms;
- dependency-aware incremental recomputation;
- safe parallelism only when scientific semantics remain deterministic or nondeterminism is explicitly recorded.

## 10. Scientific module ecosystem

CACE should grow through typed modules rather than one-off scripts.

Every production-intended module should define:

- stable identifier/version;
- typed ports;
- parameters and units;
- assumptions;
- execution function;
- verifier/certificate contract where applicable;
- evidence level;
- limitations/nonclaims;
- deterministic/reproducibility behavior;
- tests;
- example experiment.

The plugin SDK should provide compatibility/version checks, trust metadata, transactional registration, and eventually stronger process isolation/capability permissions for untrusted third-party plugins.

A long-term demo library should be searchable/loadable and should favor real reproducible examples over marketing placeholders. A useful target is roughly 100 curated demonstrations spanning multiple scientific/mathematical domains plus interdisciplinary examples.

## 11. Certified FEM/PDE direction

After proof and regression gates are secure, continue the certified PDE/FEM path:

1. mesh/topology validation;
2. finite-element spaces;
3. sparse assembly;
4. deterministic solvers;
5. residual and equilibrated-flux estimators;
6. explicit a-posteriori assumptions;
7. interval/certified error bounds where justified;
8. adaptive refinement;
9. higher-order FEM;
10. goal-oriented estimation;
11. Proof Explorer links between numerical obligations and formal dependencies.

The continuum proof chain must stay explicit. Do not claim arbitrary H1/H(div) or zero-boundary properties without the required analytic construction/hypotheses.

## 12. Geometry, algebra, and low-cost transform research

These are legitimate research directions, not established results unless separately proved/validated.

### 12.1 Graded geometry

Continue useful Clifford / projective geometric algebra / conformal geometric algebra / rotor / spinor / blade / k-cell foundations where they provide compact computation, coordinate transformations, geometry, mechanics, mesh operations, or visualization.

### 12.2 Combinatorial-to-geometric transforms

Investigate whether combinatorial groups/structures can be mapped into rotors, spinors, blades, cells, sparse graded objects, or related representations for lower-cost computation.

Requirements before promotion:

- precise mapping;
- domain/codomain and invariants;
- reversibility or information-loss statement;
- complexity comparison;
- numerical benchmarks;
- formal or exact proof of algebraic identities where feasible;
- explicit failure domains.

Custom Lean libraries/modules may be created for reusable identities once a stable mathematical formulation exists.

### 12.3 Serialization and collision-avoidance ideas

Explore mathematically structured serialization/packet scheduling ideas, including Cantor-style indexing or pairing, only when they provide a measurable benefit such as deterministic non-collision IDs, scheduling, sharding, or compact reversible addressing. Do not use mathematical metaphors as substitutes for normal network correctness/security protocols.

### 12.4 Growth/rotation random-process idea

The proposed research idea of random data generation followed by exponential-style growth and rotation in another dimension (inspired by `e^(i*pi) = -1`) may be explored as a parameterized stochastic/dynamical transform.

It must remain labeled research/heuristic until a precise state space, transform, invariant, purpose, and benchmark are specified.

## 13. Provenance, reproducibility, and Evidence Ledger

Experiments should be reproducible from versioned inputs, module contracts, source identity, dependency identity, and execution configuration.

Desired provenance chain:

`artifact -> content address -> deterministic evidence bundle / Merkle root -> signed verifier attestations -> append-only transparency/evidence ledger -> optional established external timestamp anchor`

Provenance establishes identity, history, tamper evidence, and independent reproduction. It does **not** establish mathematical truth by itself.

## 13.1 Independent run-log retention

GitHub Actions logs are a convenience surface, not the sole evidence archive. CACE should preserve critical CI, proof, qualification, deployment, and scientific-run logs independently of GitHub.

Preferred retention model:

1. **Local runner evidence store** — self-hosted runners write a complete run bundle under a durable path such as `/var/lib/cace-evidence/runs/<commit>/<run-id>/`.
2. **Persistent system journal** — runner services use persistent `systemd-journald` or equivalent host logging so process-level failures survive workflow/UI loss.
3. **OCI Object Storage mirror** — completed bundles are copied to a versioned bucket with retention/lifecycle policy; object identity is content-addressed rather than depending on a GitHub URL.
4. **Optional second mirror** — another machine, NAS, or independent object store may hold a second copy for disaster recovery.
5. **GitHub artifact/log copy** — retained when available, but never treated as the only copy.

Each run bundle should contain:

- exact source commit and branch/ref;
- workflow/job/run identity when an external orchestrator exists;
- start/end timestamps;
- command lines and step names;
- stdout/stderr captured with exit codes;
- environment/toolchain/dependency identities relevant to reproduction;
- generated manifests and diagnostic summaries;
- hashes of every stored file;
- a canonical run-manifest SHA-256;
- explicit PASS/FAIL/NOT_RUN state;
- links/digests for proof or scientific artifacts produced by the run.

The bundle should be deterministic where practical and verified after copy. An append-only local evidence ledger should record at least:

`run identity -> exact commit -> manifest digest -> storage locations -> result -> timestamp`

A missing remote copy must be visible as a provenance-storage failure, not silently converted into success or a mathematical failure.

For critical qualification paths, stdout/stderr should be captured by the command itself (for example through a wrapper/tee layer) so evidence survives even if the CI provider fails to publish its own log stream.

## 13.2 Zero-egress core, collaboration, and paid passes

CACE's scientific runtime should be network-denied by default. Network collaboration and commercial licensing should be handled by separate capability-limited brokers; see `docs/OFFLINE_COLLABORATION_AND_LICENSING.md`.

Required properties:

- no general Internet egress from the scientific worker;
- no runtime import of remote scripts, packages, modules, plugins, Lean source, or arbitrary files;
- all frontend code/assets bundled in the signed release rather than loaded from third-party origins;
- collaboration limited to authenticated, schema-versioned canvas operations and presence state;
- collaboration cannot directly set evidence/proof PASS;
- end-to-end encrypted collaboration where practical;
- viewer/editor roles, revocation, replay protection, rate/size limits, deterministic conflict handling;
- sandboxed local instances with unprivileged identity, read-only runtime, isolated workspace, resource quotas, no cloud credentials, and no arbitrary shell;
- time-limited day/week/month/year research passes;
- license expiry blocks new compute without deleting scientific work or changing evidence truth;
- Monero QR payment may fund R&D and compute infrastructure;
- payment verification produces a signed offline capability token; browser/localStorage state and arbitrary transaction hashes are never sufficient to unlock;
- pricing policy is signed/configurable and XMR conversion is quoted outside the scientific sandbox;
- local application entitlement and project-funded remote compute entitlement are distinct.

The target professional pricing band is initially approximately USD $12/day, $49/week, $149/month, and $999/year, subject to operating-cost, market, tax, and commercial validation. Pricing is product policy, not scientific source.

## 13.3 Accounts and Enterprise proof commerce

CACE supports Basic, Researcher, and Enterprise account tiers through a separate account/entitlement service. The proof runner is not an identity provider and must never receive user password material or general account/payment credentials.

- Basic: one-time 24-hour introductory entitlement; lowest pass-pricing tier.
- Researcher: one-time 48-hour introductory entitlement; middle pass-pricing tier.
- Enterprise: commercial/business engineering/scientific use; highest pass-pricing tier.
- Enterprise-only bespoke proof orders may produce customer-specific rigorous LaTeX/PDF packages after contract/payment/proof qualification gates.
- CACE Background IP remains separated from customer Foreground deliverables; see `docs/ACCOUNTS_AND_ENTERPRISE_PROOF_COMMERCE.md`.

## 13.4 Prove-before-purchase enterprise proof rule

Enterprise bespoke proof commerce follows a strict **prove first, sell second** rule.

After a customer receives a contingent quote, CACE must complete the requested proof work and the normal kernel/axiom/theorem-metadata/provenance/artifact-integrity qualification pipeline before the customer is asked to sign or pay for the final proof package.

Only a result internally marked `PROOF_READY_FOR_SALE` may proceed to statement of work, IP schedule, customer signature, payment, document rendering, and delivery.

The customer-facing proof package must pass a separate disclosure review so the agreed customer-specific derivation is rigorous while protected CACE Background IP remains undisclosed.

CACE proprietary theorem infrastructure should be protected continuously using reasonable secrecy measures such as private repositories, disclosure classification, least-privilege access, MFA/passkeys, encryption, access/export logging, confidentiality obligations, periodic access review, and mandatory pre-delivery disclosure checks. See `docs/ACCOUNTS_AND_ENTERPRISE_PROOF_COMMERCE.md`.

## 13.5 Compute capability controls by account tier

All account tiers expose a GPU acceleration ON/OFF control. CUDA is a specific NVIDIA backend and is shown only when compatible CUDA hardware/runtime is detected.

Researcher and Enterprise include CPU multithreading. Basic is single-threaded by default and may permanently unlock CPU multithreading once for USD $15 through a durable account feature entitlement.

Execution-backend controls change execution/provenance, not mathematical graph semantics or theorem truth. Numerical run records must bind the actual backend/device/thread configuration used. See `docs/ACCOUNTS_AND_ENTERPRISE_PROOF_COMMERCE.md`.

## 14. Security and production boundaries

Production hardening should include:

- least-privilege service accounts;
- no secrets in repository/client bundles;
- secure secret injection;
- dependency locks/SBOM where practical;
- CSP/CORS/auth/session hardening for the web app;
- capability restrictions around plugins and AI;
- input/schema validation;
- upload/file-size limits;
- resource quotas;
- crash recovery;
- rate limiting where appropriate;
- audit logs for mutations and privileged actions;
- fault injection/fuzzing for parsers and critical boundaries.

Formal qualification infrastructure should remain isolated from untrusted web requests.

## 15. Deployment target

The finished product should be reachable from a stable URL and usable from ordinary browsers.

A practical production shape is:

- browser static/frontend assets;
- FastAPI application API;
- Uvicorn/Gunicorn-style managed process;
- Nginx or equivalent reverse proxy;
- HTTPS;
- system service/restart policy;
- health/readiness endpoints;
- durable experiment/evidence storage;
- optional background worker/queue for long scientific jobs;
- dedicated isolated proof runner for formal qualification.

Oracle Cloud is an accepted deployment target. Heavy Lean/C++/GPU qualification jobs should not be forced into serverless runtimes. A thin serverless surface may be used only where it does not distort the architecture.

The final deployment must be testable from outside the cloud host, not merely from localhost.

## 16. Agent and repository collaboration

Any AI or developer connecting to the repository should be able to orient itself without chat history.

Minimum discoverability package:

- `AGENTS.md`;
- `AI_REPO_MAP.json`;
- `docs/STATUS.md`;
- `docs/ARCHITECTURE.md`;
- `docs/CONSTITUTION.md`;
- `docs/CLAIMS.md`;
- `docs/ROADMAP.md`;
- this master build specification;
- `docs/GOAL_REGISTRY.json`;
- deterministic generated module/claim/proof/source indexes where available.

Agents should leave useful handoffs in repository-visible structured documentation rather than relying on private chat history.

### 16.1 Complete-feature coding-agent fallback

Code builders are expected to implement the complete production feature set, not
only the subset that is easy for a generative builder.

For every required feature whose implementation is uncertain:

- preserve the current architecture first;
- generate and rank 10 candidate implementation approaches by architecture
  preservation, correctness/evidence boundary, security, tractability,
  testability/bug-sweep coverage, CACE reuse, cost, and maintainability;
- use CACE Build Lite and existing CACE modules/tools to narrow the implementation;
- build a narrowly scoped typed helper tool only when existing infrastructure is
  insufficient;
- add regression/adversarial tests and the CACE defect-family sibling sweep;
- never mark a feature complete when only a placeholder/mock exists;
- if no safe path exists, retain the ranked alternatives/blockers visibly.

All established CACE architectures remain cumulative constraints unless a later
explicit reviewed migration supersedes one.

## 17. Goal-capture protocol

When the user proposes a new goal:

1. classify it as product requirement, proof/rigor requirement, production requirement, research direction, experiment idea, or rejected/deferred idea;
2. test it against the Constitution/evidence rules;
3. keep it only if it has clear user value, scientific merit, engineering value, or research value;
4. record it in `docs/GOAL_REGISTRY.json` with status and acceptance criteria;
5. update this specification if it changes product architecture or long-term behavior;
6. never silently elevate a research idea to a verified claim;
7. never change qualification-sensitive proof source merely to document a goal;
8. prefer a documentation-only branch/commit while an exact-head qualification is running.

## 18. Dependency-ordered implementation priorities

Unless a later explicit user instruction supersedes this ordering, prefer:

1. preserve/finish exact-current-head proof qualification and provenance;
2. harden proof/sanity/CI guardrails without weakening formal scope;
3. keep repository status and agent navigation current;
4. complete browser parity for the scientific canvas;
5. add the coordinate-system/tiling visualization palette with presentation-only semantics;
6. finish Research Idea / Proposed Experiment / Build on Canvas workflow;
7. complete no-code local AI provider UX and zero-contact sandbox;
8. complete save/load/replay/export/print and evidence inspection in the web UI;
9. production API/job/storage architecture and Oracle deployment;
10. plugin isolation/security hardening;
11. certified FEM/PDE end-to-end;
12. graded-geometry/combinatorial transform research;
13. tiled/complex-base/fractal coordinate research;
14. larger demo library and advanced research modules;
15. production-release qualification.

## 19. Definition of done for the working webapp

A build should not be called a complete working CACE webapp until a user can, from a browser:

- open the Studio;
- find modules;
- drag/drop and connect a valid graph;
- edit validated parameters;
- save and reopen the experiment;
- execute full or scoped runs;
- see progress and cancellation state;
- inspect real results and visualizations;
- switch among supported coordinate/tile views without changing the underlying experiment evidence;
- toggle compatible visualizations between 2D and interactive 3D and rotate/orbit them by drag or accessible controls;
- inspect PASS/FAIL/NOT_RUN/stale evidence;
- see assumptions/nonclaims;
- inspect proof/certificate provenance when present;
- use Research Ideas and preview/build proposed graphs;
- optionally configure a local AI provider without code;
- completely disable AI;
- export/print a reproducible report;
- recover from refresh/restart without silently losing work;
- use the app from another computer over HTTPS;
- receive explicit errors when a scientific, verification, or infrastructure step fails.

Production readiness additionally requires exact-commit regression/security/deployment evidence and the formal qualification appropriate to the claims being exposed.

## 20. What CACE must never do

- claim proof from simulation alone;
- hide failed/skipped verification;
- label an AI suggestion as evidence;
- weaken a theorem or negative test to make CI green;
- treat provenance/signatures as proof;
- imply an open research problem is solved without a complete, reviewable proof;
- require AI for core operation;
- require GPU for correctness;
- require blockchain/cryptocurrency for provenance;
- let web convenience bypass canonical scientific contracts;
- let documentation commits disturb an in-flight exact-head proof qualification unnecessarily.


## Full-featured just-works product contract

CACE production is a complete mathematics/sciences playground, not a developer
prototype. Startup should automatically preflight the supported host, initialize
safe local state, start the hardened private service plane, expose only the web
gateway, detect optional backends and degrade visibly without weakening
scientific/evidence rules.

See `docs/JUST_WORKS_SELF_SANDBOXING.md`.

## Free trial and one-person account contract

The free trial requires no credit card and is granted once per verified person
identity anchor. The trial entitlement survives account recreation/deletion as
required for anti-abuse; returning users recover/merge their account rather than
receiving another trial.

Expiry is strictly non-destructive. Users retain view/export/delete/recovery/help
access to their own data while premium execution/network/economy capabilities
may be disabled until licensing.

See `CACE_TRIAL_ACCOUNT_POLICY.json` and
`docs/TRIAL_AND_ACCOUNT_UNIQUENESS.md`.

## Customer-safe complete help contract

Production help is generated from the live public module registry. Every
registered module receives visible contract help plus at least two direct-use
and two combined-module examples. Every customer-facing feature receives at
least two examples.

The help system explains typed connections, unit contracts, verification,
evidence classes, provenance and formal-qualification boundaries without
publishing proprietary CACE mathematics, algorithms, hidden defaults, theorem
bodies, source internals or security secrets.

See `CACE_PUBLIC_HELP_POLICY.json` and `docs/help/README.md`.


## Multi-user / multi-tenant production architecture

Production CACE must support many concurrent accounts while preserving strong
tenant isolation and the browser-only gateway/private-service boundary.

Preferred topology:

`load-balanced stateless gateways -> tenant control plane -> isolated tenant/job
sandboxes -> tenant-scoped durable storage`

Each account owns a durable logical CACE instance. The instance is state, identity
and capability configuration—not a private copy of the repository. All tenants
run a reviewed immutable release image so upgrades remain atomic and source does
not drift between users.

The platform should keep user-visible state continuously available while allowing
CPU/GPU/AI workers to stay warm, scale out, suspend, resume or be replaced.
Tenant-aware queues enforce quotas, backpressure and fairness.

Users may link local CACE/AI instances from their own networks through outbound
authenticated broker connections and the existing directional pairing model;
production must not require customers to open inbound firewall/router ports.

Cross-tenant database, storage, cache, job, protein, wallet and evidence access
is denied by default. Explicit collaboration/economy capabilities are the only
normal cross-tenant path.

See `CACE_MULTI_TENANT_POLICY.json` and
`docs/MULTI_TENANT_SERVICE_ARCHITECTURE.md`.
