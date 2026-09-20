# CACE Interactive Research Workbench and Visual Programming Specification

Status: product/engineering specification. Not scientific or proof evidence.

## Design goal

CACE should feel like an intuitive visual scientific programming language:
users compose typed mathematical/scientific operations on a canvas, inspect
beautiful equations and data, and run experiments without losing the exact
semantics underneath.

## Visual block-programming inspiration

Use the general high-level idea of visual block programming:

- draggable typed modules;
- clearly shaped/typed input and output ports;
- click/drag connection;
- incompatible connections rejected before execution;
- nested reusable subgraphs/functions;
- variables/constants/data sources as first-class nodes;
- loops/parameter sweeps only through explicit bounded semantic constructs;
- graph-to-text/CLI/API semantic equivalence;
- undo/redo, grouping, comments, labels and reusable templates.

CACE should use its own design, code, visual language, icons and branding.
Do not copy third-party block editor code/assets/trade dress unless a separate
license and provenance review explicitly approves it.

## Math workbench inspiration

Use only the high-level interaction pattern of a professional numerical
computing workbench:

- command/tool search;
- variable/data workspace;
- function/module browser;
- equation editor with canonical typed AST;
- formula cards;
- high-quality mathematical rendering;
- plots/tables/3D views;
- notebooks and runnable examples;
- history/replay;
- integrated Help;
- demo gallery;
- inspectable exact/numerical/formal evidence.

CACE must not clone another product's UI, branding, proprietary code, iconography,
trade dress or documentation text.

## Formula cards

A Formula Card is a user-facing projection of one canonical typed expression or
module contract. It may show:

- rendered equation;
- variables/symbols;
- units;
- domain/codomain;
- assumptions;
- compatible modules;
- evidence capability;
- one-click demo;
- "Build on Canvas";
- proof/evidence links where actually available.

The rendered formula is never the semantic source of truth; the typed AST/module
contract is.

## Animation contract

Every semantic operation should be eligible for an explanatory animation.

Examples:

- vectors/matrices transforming geometry;
- permutation/group action moving/relabeling coordinates;
- wedge/blade construction;
- affine/simplex mapping;
- mesh refinement;
- data flow through ports;
- solver iteration and residual change;
- proof/evidence state transitions;
- parameter sweeps;
- graph rewrites.

Hard rules:

- animation is derived from semantic before/after state;
- animation never changes computation order or values;
- evidence is computed independently of animation;
- animations can be disabled;
- reduced-motion accessibility is supported;
- headless/API runs are semantically identical;
- long operations show progress from real runtime events, not fake timers.

## Full-featured module language contract

A production module must behave like a usable language primitive:

discover -> understand -> provide typed input -> connect -> validate -> execute
-> verify -> inspect -> save/replay -> compose -> Help/demo -> failure recovery

Compatible ports must share canonical types/units instead of relying on
module-name-specific UI hacks.

Reusable subgraphs should be serializable as higher-level modules with explicit
contracts.

## Local-AI Top 10 next actions

Whenever the active canvas changes, the Local Research Assistant may present up
to ten grounded next actions.

Candidate sources:

- missing required inputs;
- compatible downstream/upstream modules;
- unresolved verifier/evidence steps;
- stale dependencies;
- residual/convergence behavior;
- available theorem/proof matches;
- Research Idea hypotheses;
- alternative solvers/checkers;
- visualization/inspection steps;
- reproducibility/save/export actions;
- capability gaps.

Each suggestion should include:

- action title;
- why it is relevant;
- exact affected node/module IDs;
- expected graph diff;
- prerequisites;
- approximate compute/resource cost;
- expected evidence impact;
- whether user approval is required.

The ranker should prefer useful executable actions, not novelty for its own sake.
It cannot mutate the canvas without an explicit build/run policy or user action.

## Suggested ranking signals

A deterministic baseline rank can combine:

1. objective relevance;
2. executable-now score;
3. blocker removal;
4. information gain;
5. rigor/evidence gain;
6. compatibility confidence;
7. estimated compute cost;
8. reversibility;
9. user preference/recent workflow;
10. diversity from already-listed suggestions.

The LLM can explain/re-rank within policy but should not invent unavailable
modules.

## Production acceptance

A workflow is not production-grade until the actual linked module chain,
wizard/input path, animation projection, Help, persistence, verification,
failure behavior and assistant suggestions work end-to-end.
