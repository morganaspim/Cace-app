# Gemini / Antigravity Request — CACE-KSEE Connection Phase

Status: implementation request. Consume canonical CACE contracts; do not duplicate scientific semantics.

## Read first

1. `GEMINI_CONNECTION_MANIFEST.json`
2. `docs/QUALIFIED_CAPABILITY_REGISTRY.md`
3. `docs/CACE_KSEE_ENTRY_EXPERIENCE.md`
4. `docs/LOCAL_AI_HYBRID_RUNTIME.md`
5. `docs/architecture/ADR-002-ORACLE-CI-ONLY.md`
6. `docs/SECURITY_ARCHITECTURE.md`
7. `docs/SCIENCE_MODULE_COMPLETENESS_STANDARD.md`

## Required connection work

### Capability-driven UI

Use `GET /api/capabilities` as the only normal production module palette.

Do not:

- keep a static frontend module list;
- show hidden/unqualified modules;
- infer a valid connection from matching frontend types alone;
- implement missing scientific behavior in TypeScript.

Use `POST /api/connections/validate` and `POST /api/graphs/validate`.

### Local AI

Implement UI/provider configuration for the local AI layer already defined by the
Python core.

The assistant should:

- offer Minimal / Balanced / Exploratory proposals;
- display why each proposal was suggested;
- preview the graph before mutation;
- call the canonical preview/approval/commit path;
- never expose hidden modules;
- keep AI-OFF mode fully usable.

Do not move the 385-parameter compact ranker or scientific validation truth into
browser-only state. Browser visualization may display scores/explanations; the
canonical validation remains CACE-side.

### Geometric animation

Consume `cace-geometric-animation-event-v1`.

An AI geometric action should visibly animate in the currently selected coordinate
view. Preserve the supplied semantic SHA-256; never recompute a different
scientific operation because the view changed.

Required renderer targets:

- Cartesian 2D;
- Cartesian 3D;
- projected N-D → 3D;
- hex/Eisenstein lattice;
- complex i-plane;
- omega/Eisenstein complex lattice;
- quadtree fractal;
- Morton/Z-order fractal;
- complex-radix 2i−1 fractal;
- complex-radix ω−2 fractal;
- Einstein-hat aperiodic monotile.

The complex-radix and Einstein renderers must be genuinely implemented and
visually tested. Do not substitute a decorative random tessellation and label it
Einstein. Until a renderer passes its tests, keep that view out of the production
selector.

Animation examples:

- selected point pulses/highlights;
- translation traces a path;
- rotation/rotor visibly rotates;
- reflection mirrors;
- group action shows successive states;
- Grow/random walk traces its steps;
- relationship discovery grows graph/geometry connections;
- blade/k-cell/region operations morph or highlight the relevant structure.

### CACE-KSEE shell

Implement the entry contract:

- original cinematic geometric/ASCII splash;
- CACE-KSEE name (pronounced Casey);
- Create account / Sign in / Learn about CACE-KSEE;
- copyright footer;
- post-account Research Assistant;
- skippable guided tour;
- Invite Collaborators button;
- high-level safe module Help.

Do not copy SpaceX branding/trade dress. The requested aesthetic is an original,
aerospace-clean engineering feel.

### Security

Production browser bundles must not contain proprietary scientific/proof source.

No source maps in release builds.

Use configured Production CACE backend origin. Oracle is CI only.

Implement CSP-compatible local/static frontend assets; do not fetch executable
scientific code from third-party origins.

## Required browser tests

1. static palette cannot render hidden module IDs;
2. invalid/unqualified connection is not offered and server rejection is handled;
3. valid qualified graph previews and runs;
4. AI proposal renders, previews, then mutates Canvas only after approval;
5. hidden-module AI injection is rejected;
6. one canonical geometric event preserves its semantic hash through every
   renderer;
7. Einstein renderer uses the real aperiodic monotile implementation selected for
   CACE-KSEE, not a random approximation;
8. fractal/complex-radix views are deterministic and presentation-only;
9. reduced-motion mode replaces animation with equivalent static state;
10. reconnect preserves workspace/run identity;
11. Invite Collaborators respects role/expiry/revocation;
12. no proprietary/internal Help details appear in browser-facing module docs.

## Definition of handoff complete

Return implementation evidence only after:

- browser tests pass;
- production bundle secrecy scan passes;
- all visible modules come from the qualified capability endpoint;
- all visible coordinate views have functioning tested renderers;
- local AI can propose and preview at least one complete qualified experiment;
- AI-OFF path works;
- no scientific/proof claim was promoted by frontend or AI logic.


## Shapes, matter, and molecular geometry

Read `docs/MATTER_AND_SHAPE_TOOLBOX.md`.

Add a visible **Shapes & Matter** toolbox populated from qualified capabilities,
not hard-coded fake frontend objects.

Required first items:

- Circle
- Parabola
- General Conic
- Hyperbola
- Sphere
- Hypercube
- Atom / Element
- Bond / Join
- Affine Transform

Dragging an item creates the corresponding CACE node.

Atoms/molecules must render as geometric/simulation objects only. Do not imply
force-field, reaction, orbital, energetic, or quantum-chemistry semantics that
the backend has not qualified.

3D atom/molecule/sphere rendering should use a tested 3D view. N-D hypercubes
should use a tested explicit projection such as `projected.nd_3d`.

## Conway Economic City

Read `docs/CONWAY_ECONOMIC_CITY.md`.

When and only when two or more authorized workspaces are joined through the same
collaboration link and have live federated heartbeats, expose a **City** view.

The City should animate linked AI/workspace heartbeats as a clean Conway-inspired
scientific city: cells/buildings, roads/contracts, resource flows, congestion,
cache/warehouse state, verification activity, research-interest gradients, and
Grow paths.

Consume the typed city snapshot. Do not invent economic/scientific truth in
JavaScript.

Internal scheduler credits are visual/orchestration simulation units only. Never
display them as money, cryptocurrency, account balance, subscription credit,
proof credit, or entitlement.

City visualization and AI-to-AI heartbeat context must not leak proprietary
source, secrets, unrelated user data, or proof-development internals.


Additional required browser tests:

13. shape/matter toolbox items create real qualified CACE nodes;
14. atom + atom can preview/build a bonded molecular geometric object;
15. sphere/atom/molecule render through the tested 3D view;
16. hypercube uses an explicit tested N-D projection;
17. City view remains unavailable for one/unlinked workspace;
18. two authorized linked heartbeat streams activate the City;
19. replayed/unlinked city heartbeat packets are rejected;
20. City state cannot change canonical evidence/proof state.


## Math Workspace

Read `docs/MATH_WORKSPACE.md`.

Implement a first-class **Math** entry surface backed by the qualified CACE
equation modules.

The primary experience must not look like a programming editor.

Required behavior:

- beautiful live typeset math while the user enters an equation;
- friendly keyboard input including powers, roots, fractions, Greek letters,
  trig/log functions, constants, and common implicit multiplication;
- clickable symbol/function palette;
- accessible canonical text representation;
- syntax errors shown immediately but non-destructively;
- one-click **Graph 2D**, **Graph 3D**, **Add to Canvas**, **Grow**, and **Ask AI**;
- equation Canvas cards prominently show typeset mathematics;
- technical JSON/hash/provenance details stay expandable rather than visually
  dominating ordinary math work;
- explicit and implicit 2D graph payloads use the canonical CACE output;
- 3D surfaces use the canonical CACE output and tested 3D renderer;
- local AI can summarize the bounded equation feature object and suggest
  qualified experiments/transforms;
- Grow may seed proposals from the equation but cannot invent mathematical truth.

Use `display_latex` from the CACE equation object for presentation and keep the
canonical safe expression for execution/reproducibility.

Do not send raw editor text directly into `eval`, JavaScript `Function`, or
another executable-code surface.

Any third-party math editor/typesetter added to the frontend must:

1. be locally bundled rather than loaded from a CDN;
2. have a pinned lockfile;
3. pass the CACE frontend license/SBOM gate;
4. not fetch executable code remotely at runtime.

Additional browser tests:

21. math editor round-trips canonical equation text and display LaTeX;
22. friendly `2x^2 + π` style input displays correctly;
23. malicious/programming syntax is rejected by the backend and handled safely;
24. explicit 2D equation renders from canonical samples;
25. implicit 2D equation renders the canonical zero contour;
26. explicit 3D equation renders the canonical surface;
27. Ask AI/Grow receives bounded equation features rather than arbitrary code;
28. equation-to-Canvas creation uses real qualified CACE nodes.
