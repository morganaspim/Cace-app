# CACE Post-Account Research Assistant Experience

Status: product/UX implementation specification. This document is not scientific, proof, qualification, or production-readiness evidence.

## Product identity

CACE-KSEE (pronounced **Casey**) should introduce itself as a **VRE — Verified Research Environment** for interactive rigorous mathematics and science. The pre-account splash/account flow is defined in `docs/CACE_KSEE_ENTRY_EXPERIENCE.md`.

Preferred core message:

> **Explore rigorous math with AI that learns geometric reasoning.**

Supporting description:

> CACE is a Verified Research Environment where mathematical and scientific tools can be composed visually, explored with a local research assistant, and connected to Lean-backed formal mathematics where explicit proof bindings and qualification exist.

"Verified" must not imply that every module/result is formally verified. The UI must continue to expose the actual evidence class of each result.

"AI that learns geometric reasoning" means the assistant can improve its useful behavior through local research memory, accepted CACE tools, geometric representations, prior experiment patterns, and validated reasoning workflows. It does not mean AI confidence becomes proof or that model-generated claims are automatically learned as truth.

## Default first-run journey after account creation

After a user creates/verifies an account and receives a valid entitlement, do **not** drop them directly into an empty canvas.

Show a focused welcome surface dominated by the Local Research Assistant chat.

Suggested first assistant message:

> Welcome to CACE. What would you like to investigate today?
>
> You can describe an experiment or problem in your own words, ask me to show examples relevant to your field, or explore CACE's full capabilities.

Primary actions:

- **Describe an experiment**
- **Show demos for my field**
- **Explore full capabilities**
- **Open recent work** (when recent work exists)

Secondary actions:

- Learn what makes CACE rigorous
- Browse modules
- Browse proof-backed math tools
- Open an empty canvas

The user never needs to understand CACE's internal architecture before beginning useful work.

## Conversational field discovery

The assistant should infer only the minimum useful domain context from what the user voluntarily says.

Examples:

- "I work on fluid dynamics."
- "Show me protein-related demos."
- "I want to understand finite elements."
- "I'm an electrical engineer."
- "I teach linear algebra."
- "I just want to see what CACE can do."

The assistant can then offer a compact set of relevant demos, tools, and learning paths.

Do not require users to permanently classify themselves into a field.

If the user allows workspace memory, CACE may remember useful non-sensitive research preferences and recent module choices for future sessions according to the product's memory/privacy policy.

## Demo recommendation contract

Field-specific recommendations should come from structured demo metadata, not unconstrained model invention.

Every curated demo should eventually expose metadata such as:

- demo_id;
- title;
- fields/disciplines;
- difficulty;
- estimated runtime;
- required modules;
- evidence classes demonstrated;
- mathematical concepts;
- scientific concepts;
- GPU usefulness;
- formal/Lean coverage where applicable;
- expected outputs;
- prerequisites;
- safe/sample data source;
- Help/reference links.

The LLM ranks/explains these demos. It should not fabricate a demo that is not actually available without clearly labeling it as a proposed experiment.

## From conversation to canvas

When the user describes a problem, the assistant should:

1. restate the requested objective briefly;
2. identify assumptions or missing inputs;
3. select available typed CACE modules/tools;
4. propose a small experiment graph;
5. show a preview before mutating the canvas;
6. offer **Minimal**, **Balanced**, and **Exploratory** versions where useful;
7. explain which parts are numerical, exact, interval-certified, or formally connected;
8. build the selected graph after user approval or an explicit "build it" action;
9. open the full Studio centered on the new experiment.

The transition should feel continuous: the initial chat becomes the Assistant dock/panel beside the canvas rather than disappearing.

## Studio orientation after canvas opens

On first entry, the assistant should give a short interactive tour, preferably contextual rather than modal.

Important areas:

- **Experiment Canvas** — connect mathematical/scientific modules.
- **Module Library** — tools and building blocks.
- **Properties** — inputs, parameters, units, assumptions.
- **Research Assistant** — ask questions, propose experiments, explain results.
- **Results/Data/Plots** — inspect outputs.
- **Proof Explorer / Evidence** — see what is numerical, exact, certified, or Lean-backed.
- **Research Notebook** — keep hypotheses, findings, useful/rejected ideas, and proposed experiments.
- **Performance/Provenance** — understand execution backend and reproduce runs.

The user should be able to skip the tour.

## Daily-use home experience

CACE should be useful as a daily research workbench, not only a demo application.

Returning users should see a concise research home/chat view with:

- "What are you working on today?"
- recent workspaces/experiments;
- unfinished Research Ideas;
- experiments with changed/stale dependencies;
- recent results;
- optionally suggested next steps based on local workspace context;
- relevant demos/new tools;
- quick actions for New Experiment, Resume, Compare Runs, and Explore Modules.

The Local Research Assistant should remain available throughout the day and understand the active workspace, canvas, selected nodes, notebook, and permitted local artifacts through typed CACE interfaces.

## Research Assistant roles

The assistant should be able to act as:

### Guide
Explain CACE, modules, evidence labels, mathematical notation, and where to find things.

### Builder
Translate a natural-language experiment into a typed canvas proposal.

### Research Assistant
Help formulate hypotheses, compare runs, inspect residuals, notice blockers/stale states through heartbeat/perception, organize Research Ideas, and suggest next experiments.

### Math Tutor / Geometric Reasoning Assistant
Help users interact with algebra, geometry, transforms, rotors/blades, coordinate systems, PDE/FEM structures, and visual representations while distinguishing intuition from proof.

### Rigorous Tool Collaborator
When permitted in a development workspace, propose reusable tools and follow `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`.

These roles share one assistant identity; the UI need not force the user to select a role every time.

## Local-first behavior

The preferred onboarding assistant is local.

If Local / Zero Contact mode is available:

- no research prompt needs to leave the machine;
- no external account/model provider is required for ordinary AI assistance;
- heartbeat/perception remains local;
- workspace context remains within allowed local boundaries.

If no local model is configured or healthy, CACE must still provide:

- deterministic onboarding;
- full capability browser;
- curated field demos;
- Help pages;
- manual canvas construction.

Optional remote/hybrid AI can be configured explicitly later.

## Heartbeat makes the assistant present during the experiment

Once a canvas is running, `schema/cace-agent-perception.schema.json` is the assistant's compact live state stream.

This lets it notice useful events such as:

- a residual begins worsening;
- convergence stalls;
- an upstream node changes and dependent proof/evidence becomes stale;
- a new result becomes available;
- a verifier starts/completes;
- a node blocks on missing data;
- resource pressure rises;
- a surprising result deserves research attention.

The assistant may then say, for example:

> The solver's residual stopped improving after refinement level 6. The estimator is ready, while the formal bridge is stale because the mesh changed. I can compare the last two refinements or inspect the estimator next.

This is contextual assistance, not autonomous evidence creation.

## Rigor messaging

CACE should make rigorous mathematics feel approachable without overselling formal status.

Good language:

- "Lean-backed theorem available under these assumptions."
- "This exact checker verified the finite identity."
- "This run is numerical with tolerance X."
- "This result is interval-certified over Y."
- "This runtime object is not yet formally connected to the theorem."
- "I can explain the proof dependencies."

Avoid:

- "AI proved this" when canonical qualification has not.
- "Everything in CACE is formally verified."
- "Verified" as an undifferentiated green badge.

## Suggested welcome copy

Headline:

> **CACE-KSEE — Verified Research Environment**

Subheadline:

> **Explore rigorous math with AI that learns geometric reasoning.**

Body:

> Build experiments visually, work with a local research assistant, inspect evidence and assumptions, and connect computation to Lean-backed mathematics where formal bindings are available.

Initial assistant:

> What would you like to investigate today? Describe a problem, ask for demos in your field, or let me show you CACE's full capabilities.

## Acceptance criteria

A production implementation should demonstrate that:

1. a newly entitled user lands on the Research Assistant welcome experience;
2. the assistant can route among free-form experiment intent, field demos, full-capability exploration, recent work, and empty canvas;
3. demo suggestions are grounded in real catalog metadata;
4. a conversation can produce a previewable typed graph and then Build on Canvas;
5. the initial chat persists as the Studio assistant after transition;
6. the assistant can explain evidence/proof status without manufacturing it;
7. the full onboarding path works without a cloud AI when a supported local provider is configured;
8. a no-AI fallback remains fully usable;
9. returning users can resume daily research from recent experiments/Research Ideas;
10. heartbeat/perception can provide contextual experiment updates without changing evidence state.


## Equation/data wizard handoff

When the user's request cannot safely be converted from free text alone, the Research Assistant should open the typed wizard defined in `docs/TYPED_EQUATION_DATA_WIZARD.md` rather than guessing.

Examples:

- PDE equation/domain/boundary conditions;
- units or material constants;
- tensor/vector dimensions;
- optimization constraints;
- dataset column/unit mappings;
- group action definitions;
- user-supplied mathematical expressions with ambiguous symbols.

The assistant can prefill likely fields conversationally, but the user sees the structured equation/data state, pretty mathematical rendering and deterministic validation before Build on Canvas.

This keeps conversational ease without sacrificing typed rigor.


## Grounded Top 10 next actions

After a meaningful canvas, run, notebook, or heartbeat change, the Research
Assistant may show up to ten grounded next actions.

Suggestions are generated from real state:

- active objective / Research Idea;
- selected node and graph neighborhood;
- missing required inputs;
- type/unit-compatible upstream/downstream modules;
- blockers/stale nodes;
- verifier/evidence state;
- residual/convergence signals;
- available theorem/proof matches;
- compute/resource budget;
- save/replay/compare/visualize opportunities.

Each suggestion shows a short reason, affected nodes, prerequisites, approximate
cost, expected graph change, and expected evidence impact.

The assistant should prefer actions that can actually run now and that reduce
time-to-experiment.

If a useful next action needs a capability that is not available, the suggestion
becomes **Request this capability** and follows
`docs/AI_CAPABILITY_GAP_FEEDBACK_LOOP.md`.

The Top-10 list is advisory and cannot create evidence or silently mutate the
canvas.

## Animated mathematical operations

The Studio should visually animate semantic operations when useful, including
group/permutation actions, affine transforms, blades/wedges, matrix actions,
mesh refinement, solver progress and data flow.

Animations must be projections of actual semantic state transitions. Turning
animation off, using reduced-motion mode, or running headless must produce the
same computation and evidence.


## Collaboration entry point

Once the user reaches an authorized workspace, the workspace chrome should expose
an explicit **Invite Collaborators** action. Collaboration membership and role
state come from the canonical linked-workspace service; canvas collaboration does
not grant proof promotion, billing administration, code installation, or any
other authority beyond the invited role.

See `docs/CACE_KSEE_ENTRY_EXPERIENCE.md` and the canonical collaboration/session
contracts for the detailed UI behavior.


## Product ownership footer

Splash/account/About/Help surfaces should display the subtle ownership notice:

`© 2026 Emmanuel Spiro. All rights reserved.`

This is an ownership notice, not a technical security control.
