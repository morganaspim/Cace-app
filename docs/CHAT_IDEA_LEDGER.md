# CACE Chat-Derived Idea Ledger

Status: append-only idea/research memory. **Not verification evidence.**

Purpose: preserve meritorious ideas from chats, prior handoffs, and historical CACE research files so future chats do not lose them. Mature implementation intent belongs in `docs/GOAL_REGISTRY.json`; formal truth remains in Lean + canonical qualification.

## Capture rules

- Preserve the original mathematical/product intent even when implementation is deferred.
- Mark speculative concepts as research rather than silently upgrading them.
- Link to an existing Goal ID where the goal registry already captures the idea.
- Prefer one stable entry over repeated paraphrases.
- Add refinements beneath the existing entry when possible.
- Never claim novelty in the literature unless a real literature search supports it.
- Never let this ledger promote a theorem, module, product feature, or security property.

## Recovered ideas

| ID | Area | Preserved idea | Durable mapping / state |
|---|---|---|---|
| I001 | proof/truth architecture | Explicit evidence ladder separating experimental, numerical, exact/symbolic, interval-certified, formally verified, and cross-verified evidence; no promotion by naming or AI agreement. | G001, G021 |
| I002 | typed science | Typed scientific objects with domain/codomain, shape, units, provenance, assumptions, obligations, verification state, and immutable experiment snapshots. | G004, G005, G012 |
| I003 | proof navigation | Proof Explorer / theorem dependency graph / assumption DAG that exposes exactly which hypotheses and proof endpoints support a claim. | G001, G004 |
| I004 | reliability | Fail-closed bug -> defect family -> root-cause fix -> sibling sweep -> regression -> permanent invariant/guard architecture. | G002, G024 |
| I005 | agent collaboration | Machine-readable AI collaboration records containing sender/target, exact SHA, task, evidence class, proposal, confidence, touched files, status, content hash, leases, acknowledgements, and stale-head rejection. AI consensus never equals proof. | G003, G031, G033 |
| I006 | local AI | Hybrid local assistant combining an LLM with a computationally cheap neural/ranking component and CACE-derived validated features; improve efficiency as genuinely useful proofs/transforms accumulate. | G011 |
| I007 | Grow | Grow button using seeded random walks and combinatorial/group constructions to cheaply search for patterns, experiments, and candidate relationships. | G007, G011, G020 |
| I008 | Grow UX | Animate AI/Grow transformations on coordinate systems so users can visually watch research transformations while keeping presentation separate from mathematical semantics. | G027-G029 |
| I009 | research notebook | “Keep” discoveries become editable Research Idea objects: title, notes, hypotheses, proposed experiment, associated modules, evidence, provenance, status. | G007 |
| I010 | research workflow | Research Idea lifecycle: Idea -> Testable -> Experimented -> Promising -> Proof Candidate; maturity is workflow state, not truth. | G007 |
| I011 | canvas synthesis | Proposed Experiment -> Build on Canvas with preview-before-mutation. | G008 |
| I012 | proposal strategies | Three graph proposal modes: Minimal, Balanced, Exploratory. | G008 |
| I013 | local AI UX | AI can explain experiments, modules, proofs, rigor/evidence status, failures, suggest demos/experiments, and maintain heartbeat/status during longer local work. | G009-G011 |
| I014 | AI safety | “Zero-contact” sandbox for highly capable local AI: no Internet, cloud credentials, arbitrary shell/filesystem, or silent host control; capability-mediated bounded actions only. | G010, G034 |
| I015 | model ecosystem | Evaluate reusable ideas from favorably/permissively licensed local-model ecosystems (including DeepSeek-family research ideas where licensing allows), preserving license obligations and keeping model output outside the proof TCB. | G011 |
| I016 | visualization | Coordinate palette: Cartesian square grids, triangular/hexagonal tilings, Einstein/aperiodic tilings, alternate bases, and plugin-defined coordinate renderers. | G027 |
| I017 | complex/fractal views | Base-i, omega/root-of-unity, recursively tiled, hierarchical tile-address, and fractal coordinate views; visualization-only unless an explicit semantic transform is inserted. | G028 |
| I018 | 3D UX | 2D/3D toggle; click-drag orbit left/right/up/down, zoom/pan/reset/fit, orientation gizmo and presets; camera state must not alter scientific evidence. | G029 |
| I019 | multiscale coordinates | Certified multiscale shear coordinates/tiles with finite truncations, explicit tail/error bounds, and unresolved ownership near ambiguous boundaries. | Research; G028 |
| I020 | Hilbert coordinates | Tail-certified Hilbert coordinates: finite prefix/support address plus residual oracle; never pretend finite plots exactly store infinite-dimensional data. | Research; G028 |
| I021 | product mosaics | Complex product mosaics combining hexagonal, simplex, shear, or other factors in declared product/complex spaces. | Research; G028 |
| I022 | adaptive dimensions | Choose the smallest finite prefix/dimension meeting an explicit certified error budget. | Research |
| I023 | curved cells | Smooth periodic lens/shear cells such as F(x,y)=(x+A sin(2πy),y), conditioned on invertibility, distortion, boundary certification, conditioning, and performance analysis. | Research |
| I024 | coupled shears | Compose invertible periodic shears across multiple coordinate pairs; investigate equivariance, volume, distortion, conditioning, and performance. | Research |
| I025 | graded geometry | Clifford/PGA/CGA foundations using vectors, bivectors, rotors, spinors, blades and k-cells with sparse graded representations. | G017 |
| I026 | combinatorial geometry | Translate combinatorial structures/groups into rotors, spinors, blades, k-cells, or sparse geometric objects for potentially cheaper computation; specify invariants, reversibility/loss, and benchmarks. | G018 |
| I027 | custom formal library | Build reusable custom Lean modules for stable CACE identities/combinations; investigate smaller self-owned formal libraries only if rigor and licensing are preserved. Never replace the trusted proof kernel with an unqualified shortcut. | Research / proof tooling |
| I028 | exact transforms | Certified affine normalization to reference cells; affine/Piola transport; determinant/product fusion; exact transported P1/RT0 identities; normalizer and assembly transport. | Current formal lineage |
| I029 | discrete checker | Exact P1/RT0 discrete Green-identity checker and rational finite-mesh certificate path. | Certified FEM/PDE lineage; G016 |
| I030 | continuum PDE | Sobolev/H1 -> H(div) graph spaces -> Green -> trace -> density/closure -> weak Green -> orthogonality -> Prager–Synge. | Current formal spine |
| I031 | theorem batching | Rank theorem candidates by gap closure, leverage, tractability, reuse and rigor safety; batch compatible quarantined modules to minimize manual runner dispatches. | G046; v3.41 roadmap |
| I032 | H1-zero concrete core | Smooth face-vanishing scalar core, classical flux cancellation, functional trace extension, graph closure, pairwise cancellation, concrete box H1-zero Prager–Synge. | `docs/proofs/V341_TOP20_OF50_THEOREM_ROADMAP.md` |
| I033 | q-side boundary core | Smooth zero-normal H(div) submodule and closure path so flux-side boundary conditions can discharge pairings. | v3.41 candidates 25–30 |
| I034 | mixed boundaries | Face-mask representation for complementary Dirichlet/Neumann conditions and mixed-boundary Prager–Synge/hypercircle results. | v3.41 candidates 31–37 |
| I035 | bubble core | Polynomial box boundary bubble, face-vanishing proof, Schwartz-preserving multiplication, bubble-generated H1-zero core. | v3.41 candidates 38–43 |
| I036 | compact support | Interior compact-support smooth scalar core and safe one-way inclusion into concrete H1-zero graph space; equality only under explicit approximation criteria. | v3.41 candidates 44–48 |
| I037 | Hdiv density | Real whole-space H(div) density via careful real/complex reasoning, and later bounded-domain H(div) density / normal-trace core theorem. | v3.41 candidates 49–50 |
| I038 | stochastic transform | Random walk X_n, growth operator G_t (possibly exp(tA)), and rotation/isometry R_t; geometric-algebra form R=exp(-B theta/2), x'=R x R^-1 where defined. Study invariants, stability, ergodicity, embeddings, covariance and spectral effects. | G020 |
| I039 | Cantor addressing | Cantor/Hilbert-hotel-inspired injective tuple addresses for deterministic IDs, scheduling and sharding; mathematical uniqueness must remain separate from locks/network correctness. | G019 |
| I040 | deterministic scheduler | Address -> resource class -> deterministic slot/queue -> execution -> content hash -> ledger; separately handle fairness, starvation, cancellation recovery and actual networking. | G019, G023 |
| I041 | serialization/parallelism | Plan deterministic serialization so safe independent work can later run in parallel without proof-job collisions or evidence ambiguity. | G019, G046 |
| I042 | cache architecture | Persistent Lean/Mathlib cache, dependency-aware builds, and local prewarm to reduce repeated cost; cache accelerates work but is never proof evidence. | G001, G046 |
| I043 | run evidence | Provider-independent logs: local runner evidence directory, persistent host journal, content-addressed manifests, remote mirror target such as OCI Object Storage. | G030 |
| I044 | browser Studio | Full scientific drag/drop + typed click-connect browser canvas, not a thin demo; shared semantics with desktop/CLI/agent. | G004, G012, G022 |
| I045 | collaboration | Future invite-only/local-network shared canvas with typed operations and zero-general-egress scientific core. | G032, G033 |
| I046 | save/export | Save/replay versioned .cace experiments, evidence bundles, report/export/print, recovery/autosave, deterministic fingerprints. | G006 |
| I047 | compiled/navigation context | Make the repo easy for any connected AI by generating deterministic module/claim/proof/source indexes and consolidated source context rather than maintaining a conflicting duplicate code tree. | G003, G031 |
| I048 | legacy scientific domains | Preserve useful older CACE tracks as research candidates: Navier–Stokes computational research, Stokes, Maxwell, DG/SUPG, sparse eigensolvers, optimization, topology/high-dimensional coordinates, arbitrary precision and self-similarity. | G016 plus research backlog |
| I049 | quantum research | QAOA, boson sampling/loss, spin systems and related quantum examples remain research modules with explicit evidence ceilings; benchmark success is not a supremacy/theorem claim. | Research backlog |
| I050 | broader module ecosystem | Statistics, ODEs, ML, signal/sensor, geometry/robotics, biology/chemistry geometry and interdisciplinary examples should be migrated only as typed, reproducible modules with assumptions and limits. | G015, G025 |
| I051 | adaptive/Conway research | Preserve adaptive/deformed Conway-style architecture, Growth Loop toggles, and seed+hash deterministic stochastic experiments as research concepts requiring explicit semantics before promotion. | Research backlog |
| I052 | scientific/neural export | Investigate compiled/exportable scientific or neural environments while preserving exact source/model/dependency provenance. | Research / G006, G013 |
| I053 | view vs semantic rotation | Camera/view rotation is presentation-only; scientific object rotation must change semantic identity, invalidate dependent evidence, persist in .cace, and appear in run identity. | G029 / architecture invariant |
| I054 | generally-useful mode | Preserve the idea of a GUI “Generally Useful” research/AI mode or button that favors broadly reusable discoveries rather than one-off results; define scoring/semantics before implementation. | Research UX |
| I055 | cross-chat continuity | Every substantive CACE chat retrieves the durable handoff, preserves new meritorious ideas, refreshes current state, and mirrors the handoff outside GitHub. | New continuity goal G047 |


| I056 | reasoning pedagogy | Train the local AI on reusable typed operations and operation sequences rather than static answer surfaces; curriculum progresses from single operators to compositions, inverse problems, counterfactuals, transfer and discovery. | New design: `docs/LOCAL_AI_REASONING_CURRICULUM.md`; G048 |
| I057 | anti-memorization eval | Use independently generated canonical/perturbed paired tasks where load-bearing changes require answer changes, alongside irrelevant perturbations that require invariance; evaluate pair correctness, necessary flips, invariance, transfer and composition holdouts. | G048 |
| I058 | geometric reasoning | Compress chaotic observations into typed relational/geometric structures, symmetries, invariants, sparse operator programs and checkable transformations instead of brute-force all-pairs association. | G048; related G017-G020 |
| I059 | operator memory | Maintain a learned operator library with preconditions, invariants, inverses, commutation/composition rules, costs, failure domains and linked CACE checkers rather than an answer notebook. | G048 |
| I060 | canvas heartbeat | Connect canvas items and the local AI through a deterministic Conway-inspired cellular heartbeat/state field for readiness, activity, waiting, stale, verification, failure and research attention; heartbeat can guide attention but never verification. | G049 |


| I061 | molecular science | Add typed atoms, bonds and molecules as draggable scientific objects, with geometry/provenance/evidence metadata and safe household chemistry experiment support. | G050 |
| I062 | protein folding | Import AlphaFold-compatible predictions with attribution and run deterministic low-cost coarse folding/refinement, reporting only the lowest energy found rather than claiming a proven global minimum. | G051 |
| I063 | materials discovery | Search/generate material hypotheses using composition, symmetry and mathematical descriptors with explicit uncertainty and evidence provenance; connect promising candidates to Research Ideas. | G052 |
| I064 | physics canvas | Add draggable Standard Model particles, fields and clearly theoretical string/brane/worldsheet objects, with established-vs-theoretical classification and quark-confinement caveats. | G053 |

| I065 | protein playground | Keep AlphaFold as an external attributable protein-data source rather than reproducing its model; imported proteins become immutable CACE objects with residue heartbeats and a GUI Play button that routes bounded structural context to the local AI. | G051 |
| I066 | open-problems toolkit | Curated, date-stamped open-problem catalogs (starting with the Millennium problems) can be searched in the GUI, imported as typed canvas objects, and explored with heartbeat-guided local AI while preserving source/status and never equating AI exploration with a solution. | G054 |

| I067 | heartbeat economy | Extend the Conway-inspired canvas heartbeat into a bounded internal compute economy: spare CPU/GPU headroom mints non-monetary research credits, tasks bid for exploration budget, and scheduling strategies optimize against externally measured useful work rather than AI self-scores. | G055 |
| I068 | high-capability AI gate | Add a default-OFF GUI gate for future superintelligence-class providers. OFF blocks that declared capability tier; ON merely permits admission while separate sandbox/network/self-modification/evidence/resource controls still apply. | G056 |
| I069 | latent matrix observers | For instrumentable local/open neural models, export copies of hidden-layer matrices through a one-way host broker to multiple immutable observer containers; model inference receives no feedback/control channel from observers. | G057 |

| I070 | math coin | A fixed 500B-supply, no-mining Math Coin acts as a scarce external compute-right for the Conway heartbeat economic city: most supply is locked in a time vault, discrete tranches unlock only every 10 years, compute consumption burns MATH after measured settlement, and AI agents may trade through a bounded broker against real crypto without direct wallet-key authority. | G058 |

| I071 | alphafold db api | Resolve a UniProt accession through the current public AlphaFold DB prediction API, use its version-current PDB URL instead of guessed filenames, preserve CC-BY-4.0 attribution/hashes, place the API source on the canvas, auto-run it, and expose the returned typed protein structure to Protein Playground heartbeat Play. | G051 |

| I072 | coding-agent completion fallback | A production coding agent must attempt every requested CACE feature; if it does not know how, generate and rank 10 implementation approaches, use CACE Build Lite/existing CACE math/tools to choose an architecture-preserving path, or build a narrow regression-tested helper tool with bug-sweep guardrails. Never silently drop a feature or replace an established architecture for convenience. | G059 |
| I073 | directional AI economy pairing | Network stays off by default; enabling it issues separate short-lived receive/outgoing codes. A directed local-AI economy link consumes source-outgoing + target-receive codes and grants only narrow economy/heartbeat capabilities. Account profiles carry declared user type/location scope, optional protein-library consent, and a Math Coin AI-wallet identity separate from canonical XMR custody. | G060 |

| I074 | browser-only gateway | Make the webapp/gateway the only client-visible CACE surface. Everything privileged—scientific runtime, AI, databases, pairing/economy/payment brokers, filesystem/native workers and Lean qualification—runs in a hardened local/private service plane reached only through typed server-side mediation. | G061 |

| I075 | customer-safe complete help | Generate a complete help/reference file from the live registry: every feature/module gets public inputs/outputs/parameter type/unit guidance, rigor/evidence explanations, at least two examples and two combined-module examples, while proprietary equations, algorithms, hidden defaults, theorem bodies and source internals remain secret. | G062 |
| I076 | just-works one-person trial | Production CACE should be a full-featured maths/sciences playground that preflights and self-sandboxes automatically; the no-card free trial is one per verified person and survives account recreation, while expiry is transparent/non-destructive and preserves view/export/delete/recovery access. | G063 |

| I077 | multi-tenant persistent CACE instances | Scale CACE to many users using stateless load-balanced gateways, one durable logical instance per account, tenant-scoped persistent state and isolated elastic sandboxes. Local CACE/AI on customer networks connects outbound through the pairing broker; warm/suspend/resume workers preserve an always-available experience without per-user source clones. | G064 |

| I078 | public signup privacy-preserving feedback loop | Operate one stable public CACE signup URL for eligible users, block CN/KP at the trusted edge per product policy, give each user a durable tenant instance, and collect strict allowlisted operational/heartbeat/proof-status metadata plus privacy-controlled aggregate usage analytics for product/sales improvement; actual proof/research content is a separate explicit opt-in. | G065 |

| I084 | Base44 two-way GitHub sync boundary | Use Base44 as a two-way synced customer-facing web/product builder while GitHub remains canonical. Base44 gets a narrow direct-write zone, joint API/schema review zone, protected proof/science/security/wallet paths, schema-only database sync, CODEOWNERS, and a strict actor/branch-aware CI guard. | G071 |

## Current theorem idea inventory

The exact ranked list of 50 theorem candidates and selected top 20 is intentionally not duplicated here. Its canonical planning document is:

`docs/proofs/V341_TOP20_OF50_THEOREM_ROADMAP.md`

That file preserves dependency order and the v3.41A–E partition.

## Historical recovery sources

When searching for additional older ideas, prioritize these Library files:

- `CACE_MASTER_TIMELINE_FEATURES_MATH_PROOFS_IDEAS_2026-09-17.txt`
- `CACE_FULL_REMAINING_PLAN_2026-09-14.txt`
- `INFINITE_EXTENSION.md`
- `THEORY.md`
- prior exact-continuation/remaining-plan handoffs

If a future chat recovers a meritorious idea that is not represented above or in the goal registry, append it with a new stable I-ID rather than overwriting history.
