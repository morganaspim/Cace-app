# M.E.R.L.I.N. — Classical Reference Frames v23 and full-project gate map

**Research-only / independent offline implementation.** The previous CACE goal registry had 83 goals G001–G083 and idea ledger I001–I102 before this addition. This update appends G084 and I103–I105 without rewriting earlier intent. The complete historical raw chat archive is not available; sources are current connected repository records plus the locally tested v23 companion artifact.

## Verified local prototype (not canonical CACE runtime)

The independently created package `MERLIN_Classical_Reference_Frames_and_Project_Roadmap_v23.zip` contains 18 passing local tests and a separate v22 atlas regression with 22 passing tests. An original M.E.R.L.I.N. six-character council prototype produced 12 simulated comments and six hypotheses, labelled advisory. Sample residuals: three-frame cocycle 2.22e-16; affine geometric conservation 5.55e-17. These values are floating point synthetic/model-relative, not physical measurements or formally verified claims. This repository includes a compact research reference and selected CI tests; do not infer the external ZIP is deployed.

### Mathematics
For `x=X(t)+R(theta(t))q` the inertial acceleration is
`A + R(qdd + 2 omega J qdot + alpha J q - omega^2 q)`, where `J(x,y)=(-y,x)`. An inertial frame changes to a uniformly translated Galilean frame without adding acceleration; noninertial terms follow from differentiating the moving axes. For three frames, require `T_BC(T_AB(q,t),t)=T_AC(q,t)`; this describes one worldpoint, not multiple physical events.

For `x=M(t)q+b(t)`, `J=det(M)` and `dJ/dt = div_q[J M^-1 w]` with mesh velocity `w=partial_t x|q`. The implemented diagonal scale/rotation special case checks `d(ab)/dt=ab(a_dot/a+b_dot/b)`. This is a kinematic geometric conservation identity, not full ALE PDE accuracy or fixed-domain mass conservation.

## Ranked open acceptance gates / complete project coverage principle

1. **Exact-head truth gate — G001, G002, G060, G082:** CACE full Python/native, bug-sweep, qualification-drift and pinned Lean authority; scoped collaboration CI does not substitute.
2. **Canonical rigorous math kernel — G061/G062:** typed exact C++ foundational tools, Python orchestration and explicit Lean bindings.
3. **Permission/authenticated agent runtime — G010, G024, G056, G066, G080:** trusted tool broker, no-egress mode, source/scope receipts; model permission labels alone cannot grant action.
4. **Classical multi-frame baseline — G083/G084:** research-only code/tests here; next typed Research Notebook experiment API review and independent numerical baselines.
5. **Moving mesh + QRF — G083:** discretized ALE free-stream preservation, curved geometry, published quantum-reference-frame reproduction; no false superposition claim from ordinary coordinate transforms.
6. **Project-only council, ideas, research memory — G007/G008/G048/G066/G078–G081:** integrate source-linked council deliberation and Ideonomy hypothesis objects with rights/consent, and test vs a single-model baseline.
7. **CACE browser Studio and science modules — G004–G006/G016–G020/G050–G053/G063–G075:** prioritize math kernel → proof-backed toolbox → composable modules → examples/Help before major browser polish.
8. **Automated training/evolution & private iPhone AI — G009/G048/G056/G077:** measured held-out model improvement, guarded code proposals, authentic local device tests, safe resources and rollback.
9. **MCFC physics/glyph speculative programme:** exact physical models, negative controls, literature reproduction and independently observed measurement; no quantum wormhole/TOE qualification inferred.
10. **Release/security/business and monitoring — G021–G046/G055–G070:** checked code isolation, provenance, account/licensing, source secrecy, performance, reliability, legal deployment and provenance audits.

**Status rule:** The registry records intentions, not verified completion. A September CACE STATUS.md snapshot is stale relative to this branch, so unknown goals must be marked `UNASSESSED_AT_CURRENT_HEAD` until reviewed against exact current code and CI. For each new iteration, update the full 84-goal matrix below without reclassifying documentation or synthetic data as evidence.

## Source-backed research

- TU Delft noninertial dynamics: https://qiweb.tudelft.nl/mecharela/noninertialframes/
- Cline rotating reference frames: https://phys.libretexts.org/Bookshelves/Classical_Mechanics/Variational_Principles_in_Classical_Mechanics_%28Cline%29/12%3A_Non-inertial_Reference_Frames
- Fu, Schnücke, Xia (2019), moving simplex ALE-DG: https://doi.org/10.1090/mcom/3417
- Mavriplis/Yang moving-grid discrete GCL: https://doi.org/10.1016/j.jcp.2005.08.018
- Clelland classical moving-frame geometry: https://doi.org/10.1090/gsm/178
- Giacomini (2021) spacetime quantum reference frames: https://doi.org/10.22331/q-2021-07-22-508

## Goal audit index — no invented completion states

| Goal | Category | Implementation objective | Evidence audit |
|---|---|---|---|
| G001 | proof_rigor | Fail-closed exact-current-head formal qualification | UNASSESSED_AT_CURRENT_HEAD |
| G002 | ci_rigor | Self-validating source and proof sanity checks | UNASSESSED_AT_CURRENT_HEAD |
| G003 | agent_readiness | Repository-contained project memory | UNASSESSED_AT_CURRENT_HEAD |
| G004 | webapp | Full browser scientific canvas | UNASSESSED_AT_CURRENT_HEAD |
| G005 | webapp | Browser execution and evidence inspection | UNASSESSED_AT_CURRENT_HEAD |
| G006 | reproducibility | Save, replay, export, and print | UNASSESSED_AT_CURRENT_HEAD |
| G007 | research_notebook | Research Idea objects | UNASSESSED_AT_CURRENT_HEAD |
| G008 | research_notebook | Proposed Experiment -> Build on Canvas | UNASSESSED_AT_CURRENT_HEAD |
| G009 | ai | No-code optional local AI | UNASSESSED_AT_CURRENT_HEAD |
| G010 | ai_security | Zero-contact local AI sandbox | UNASSESSED_AT_CURRENT_HEAD |
| G011 | ai_research | Hybrid local neural + LLM assistant | UNASSESSED_AT_CURRENT_HEAD |
| G012 | runtime | Shared desktop/web/CLI/agent semantics | UNASSESSED_AT_CURRENT_HEAD |
| G013 | native_compute | Python orchestration with justified C++20 kernels | UNASSESSED_AT_CURRENT_HEAD |
| G014 | gpu | Optional GPU with truthful provenance | UNASSESSED_AT_CURRENT_HEAD |
| G015 | plugins | Typed plugin/module SDK with isolation | UNASSESSED_AT_CURRENT_HEAD |
| G016 | scientific_modules | Certified FEM/PDE end-to-end | UNASSESSED_AT_CURRENT_HEAD |
| G017 | geometry_research | Graded geometry and Clifford/PGA/CGA foundations | UNASSESSED_AT_CURRENT_HEAD |
| G018 | math_research | Combinatorial-to-geometric low-cost transforms | UNASSESSED_AT_CURRENT_HEAD |
| G019 | math_research | Structured serialization and collision-avoidance research | UNASSESSED_AT_CURRENT_HEAD |
| G020 | math_research | Growth/rotation stochastic transform | UNASSESSED_AT_CURRENT_HEAD |
| G021 | provenance | Content-addressed Evidence Ledger | UNASSESSED_AT_CURRENT_HEAD |
| G022 | deployment | Production browser deployment | UNASSESSED_AT_CURRENT_HEAD |
| G023 | deployment | Isolate heavy scientific/proof jobs from web requests | UNASSESSED_AT_CURRENT_HEAD |
| G024 | security | Production security and fault tolerance | UNASSESSED_AT_CURRENT_HEAD |
| G025 | examples | Curated reproducible demo library | UNASSESSED_AT_CURRENT_HEAD |
| G026 | release | Production definition of done | UNASSESSED_AT_CURRENT_HEAD |
| G027 | visualization | Coordinate-system visualization palette | UNASSESSED_AT_CURRENT_HEAD |
| G028 | visualization_research | Tiled, complex-base, and fractal coordinate views | UNASSESSED_AT_CURRENT_HEAD |
| G029 | visualization | Interactive 2D/3D visualization toggle | UNASSESSED_AT_CURRENT_HEAD |
| G030 | provenance_operations | Provider-independent run-log retention | UNASSESSED_AT_CURRENT_HEAD |
| G031 | agent_readiness | Repository-only build and trust reconstruction | UNASSESSED_AT_CURRENT_HEAD |
| G032 | security | Zero-egress scientific webapp core | UNASSESSED_AT_CURRENT_HEAD |
| G033 | collaboration | Invite-only network shared canvas | UNASSESSED_AT_CURRENT_HEAD |
| G034 | security | Sandbox every local CACE instance | UNASSESSED_AT_CURRENT_HEAD |
| G035 | licensing | Day/week/month/year Monero research passes | UNASSESSED_AT_CURRENT_HEAD |
| G036 | commercial | Professional scientific-software pricing policy | UNASSESSED_AT_CURRENT_HEAD |
| G037 | identity | Account login with hardened password storage | UNASSESSED_AT_CURRENT_HEAD |
| G038 | licensing | Durable entitlement and payment ledger | UNASSESSED_AT_CURRENT_HEAD |
| G039 | enterprise | Enterprise full-rigor proof purchase workflow | UNASSESSED_AT_CURRENT_HEAD |
| G040 | enterprise | Separate CACE Background IP from customer Foreground deliverables | UNASSESSED_AT_CURRENT_HEAD |
| G041 | security | Separate proof runner from account, contract, and email credentials | UNASSESSED_AT_CURRENT_HEAD |
| G042 | trade_secret_security | Continuous reasonable-measures protection for proprietary theorem corpus | UNASSESSED_AT_CURRENT_HEAD |
| G043 | compute_entitlements | Tiered GPU/CUDA and CPU multithread controls | UNASSESSED_AT_CURRENT_HEAD |
| G044 | source_secrecy | Fail-closed source-secrecy release gates | UNASSESSED_AT_CURRENT_HEAD |
| G045 | runtime_security | Minimal CPU/GPU plaintext exposure | UNASSESSED_AT_CURRENT_HEAD |
| G046 | proof_operations | Minimize user-triggered proof jobs through batched qualification | UNASSESSED_AT_CURRENT_HEAD |
| G047 | agent_readiness | Cross-chat continuity and redundant idea handoff | UNASSESSED_AT_CURRENT_HEAD |
| G048 | ai_reasoning | Reasoning-first local AI curriculum and anti-memorization evaluation | UNASSESSED_AT_CURRENT_HEAD |
| G049 | ai_canvas_coordination | Conway-inspired canvas and local-AI heartbeat field | UNASSESSED_AT_CURRENT_HEAD |
| G050 | molecular_science | Typed atoms, molecules, and safe home-lab chemistry | UNASSESSED_AT_CURRENT_HEAD |
| G051 | protein_science | License-safe protein structure import and low-cost fold search | UNASSESSED_AT_CURRENT_HEAD |
| G052 | materials_research | Mathematical materials candidate screening | UNASSESSED_AT_CURRENT_HEAD |
| G053 | physics_visualization | Typed draggable particle, field, and theoretical physics objects | UNASSESSED_AT_CURRENT_HEAD |
| G054 | research_navigation | Open Problems Toolkit with canvas import and AI Play | UNASSESSED_AT_CURRENT_HEAD |
| G055 | compute_orchestration | Conway heartbeat spare-compute economy | UNASSESSED_AT_CURRENT_HEAD |
| G056 | ai_security | Default-off superintelligence-class capability gate | UNASSESSED_AT_CURRENT_HEAD |
| G057 | ai_observability | Immutable one-way deep-layer matrix observers | UNASSESSED_AT_CURRENT_HEAD |
| G058 | compute_economy_crypto | Math Coin burn-to-compute heartbeat economy | UNASSESSED_AT_CURRENT_HEAD |
| G059 | ai_development_governance | Gemini-first AI builder contract with evidence isolation | UNASSESSED_AT_CURRENT_HEAD |
| G060 | proof_rigor | Concrete runtime-to-formal P1/RT0 and continuum linkage | UNASSESSED_AT_CURRENT_HEAD |
| G061 | math_kernel | CACE Rigorous Math Kernel v1 | UNASSESSED_AT_CURRENT_HEAD |
| G062 | math_toolbox | Broad proof-backed mathematical toolbox | UNASSESSED_AT_CURRENT_HEAD |
| G063 | scientific_modules | Full-featured composable science modules | UNASSESSED_AT_CURRENT_HEAD |
| G064 | help_examples | Integrated module Help pages and runnable example library | UNASSESSED_AT_CURRENT_HEAD |
| G065 | ai_context | Bounded AI context pack for Gemini and Antigravity | UNASSESSED_AT_CURRENT_HEAD |
| G066 | ai_agent_runtime | Provider-independent local agent runtime with heartbeat recovery | UNASSESSED_AT_CURRENT_HEAD |
| G067 | ai_rigorous_tooling | AI-built C++ tools with formalization and proof-ready handoff | UNASSESSED_AT_CURRENT_HEAD |
| G068 | research_assistant_ux | Research-assistant-first post-account onboarding and daily workspace | UNASSESSED_AT_CURRENT_HEAD |
| G069 | proof_discovery | Experiment-to-proof discovery loop | UNASSESSED_AT_CURRENT_HEAD |
| G070 | production_completeness | End-to-end production completeness gate | UNASSESSED_AT_CURRENT_HEAD |
| G071 | input_ux | Typed equation and data wizard with high-quality math rendering | UNASSESSED_AT_CURRENT_HEAD |
| G072 | ai_math_efficiency | Combinatorial and group-action reasoning acceleration | UNASSESSED_AT_CURRENT_HEAD |
| G073 | ai_capability_feedback | Capability-gap feedback to rigorous tool incubation | UNASSESSED_AT_CURRENT_HEAD |
| G074 | visual_programming | Typed visual scientific programming language with semantic animation | UNASSESSED_AT_CURRENT_HEAD |
| G075 | math_workbench | Independent mathematical workbench with formula cards and beautiful typed input | UNASSESSED_AT_CURRENT_HEAD |
| G076 | research_assistant_planning | Grounded Top-10 next-actions assistant | UNASSESSED_AT_CURRENT_HEAD |
| G077 | ai_math_efficiency | Benchmark-driven math-guided neural efficiency | UNASSESSED_AT_CURRENT_HEAD |
| G078 | research_ideation | Source-grounded Ideonomy product and scientific idea combinatorics | UNASSESSED_AT_CURRENT_HEAD |
| G079 | historical_multidisciplinary_research | Case-study AI history, historical esotericism and unexplained-mystery research | UNASSESSED_AT_CURRENT_HEAD |
| G080 | research_reasoning | Requirements-first independent abductive investigation and source-aware lens routing | UNASSESSED_AT_CURRENT_HEAD |
| G081 | project_memory_and_learning | Portable MCFC–CACE project-only investigative skill and historical-critical learning corpus | UNASSESSED_AT_CURRENT_HEAD |
| G082 | engineering_reliability | Project-only fail-fast pre-PR coding and permanent bug-family clearing | UNASSESSED_AT_CURRENT_HEAD |
| G083 | math_research | Multi-frame living coordinate atlas and quantum relational mathematics research | UNASSESSED_AT_CURRENT_HEAD |
| G084 | classical_reference_frames | Classical reference-frame dynamics and evolving mesh benchmark baseline | LOCAL_PROTOTYPE_PASS; REPO_CI_NOT_RUN |

Future agents must attach exact-commit source, test and operational receipts before marking implementation, qualification or deployment as complete.
