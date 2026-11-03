# CACE-KSEE Math Workspace

Status: product + typed scientific contract. Parsing/sampling is engineering/numerical
functionality and does not by itself establish formal proof.

## Goal

Entering mathematics should feel closer to writing mathematics than writing code.

A user should be able to type or visually compose expressions such as:

```text
y = 2x^2 + sin(x)
x^2 + y^2 = 4
z = sin(x) cos(y)
f(x) = exp(-x^2)
```

and immediately obtain:

- beautiful typeset math;
- safe canonical CACE equation state;
- 2D or 3D graphing when supported;
- structural feature summaries;
- compatible CACE modules;
- optional local-AI explanation;
- optional Grow/experiment suggestions;
- reusable equation objects on Canvas.

## Canonical core

Files:

- `cace_studio/core/expression_math.py`
- `cace_studio/modules/equations.py`

Production modules:

- `math.custom_equation`
- `math.equation_features`
- `math.graph_equation_2d`
- `math.graph_equation_3d`

The expression language does **not** use Python `eval`. It parses a strict
allowlist of real-number mathematical syntax and rejects attributes, imports,
subscripts, comprehensions, lambdas, arbitrary function calls, strings, and other
programming constructs.

## Friendly input

CACE normalizes common mathematical input:

- `^` -> exponentiation;
- `π` -> pi;
- `×` / middle dot -> multiplication;
- `÷` -> division;
- `ln(...)` -> natural logarithm;
- `√(...)` -> square root;
- common implicit multiplication such as `2x`, `3pi`, `2(x+1)`.

Supported core functions include trigonometric/hyperbolic functions, inverse
trigonometric functions, exp/log/log10, sqrt, abs, floor, ceil, and atan2.

The backend returns both:

- a canonical safe expression used for execution/reproducibility;
- `display_latex` used only for beautiful presentation.

The displayed math and canonical equation refer to the same stored equation
object.

## Visual math input

Gemini/Antigravity should implement a dedicated math-entry component, not a plain
programming textarea as the primary experience.

Recommended interaction:

```text
┌──────────────────────────────────────────────────────────┐
│  y = 2x² + sin(x) + π                                   │
│                                                          │
│  [ beautifully typeset live preview ]                    │
├──────────────────────────────────────────────────────────┤
│ Graph 2D   Graph 3D   Add to Canvas   Grow   Ask AI      │
└──────────────────────────────────────────────────────────┘
```

Requirements:

- direct keyboard input;
- clickable symbol/function palette for users who prefer it;
- fractions, powers, roots, Greek letters, subscripts/presentation labels, parentheses,
  trig/log functions, and common constants supported by the current grammar;
- hide matrix/tensor controls until a corresponding typed CACE matrix-expression contract is qualified;
- clear cursor/caret behavior;
- paste from plain mathematical text;
- an accessible text representation;
- immediate syntax feedback;
- autocomplete limited to supported mathematical functions/symbols;
- no programming-language autocomplete;
- keyboard shortcuts should never require LaTeX knowledge;
- optional advanced raw/canonical view for expert users;
- high-quality mathematical typography;
- dark/light theme compatibility;
- screen-reader-accessible canonical text.

If Gemini selects a third-party browser math editor or renderer, it must be
locally bundled and pass CACE's frontend dependency/license/SBOM gate before
production. No CDN script is required to use the Math Workspace.

## Graphing

### 2D

`math.graph_equation_2d` supports:

- explicit one-variable equations such as `y = sin(x)`;
- explicit `x = f(y)`;
- one-argument function definitions;
- implicit two-variable equations such as `x^2 + y^2 = 4`.

Explicit curves return deterministic sampled points.

Implicit curves return a deterministic residual grid; the GUI renders the
zero-level contour.

Users can pan, zoom, inspect coordinates, animate compatible transforms, and
switch presentation coordinate views where meaningful.

### 3D

`math.graph_equation_3d` v1 supports explicit two-variable surfaces such as:

```text
z = sin(x) cos(y)
f(x,y) = exp(-(x^2+y^2))
```

The module returns deterministic sampled grids for the 3D renderer.

Implicit 3D is intentionally not claimed by v1. It should be promoted separately
with a tested isosurface workflow.

## Equation feature summary

`math.equation_features` provides bounded structural metadata such as:

- free symbols;
- declared arguments;
- expression/equation type;
- functions used;
- operator families;
- power count;
- syntax complexity;
- supported graph modes.

This is ideal low-cost context for Grow and the local AI.

It is descriptive metadata, not mathematical truth about roots, extrema,
stability, convexity, topology, solvability, or proof status.

## AI interaction

The Research Assistant may offer actions such as:

- **Summarize this equation**
- **What features stand out?**
- **Graph it**
- **Suggest an experiment**
- **Suggest compatible transforms**
- **Compare with another equation**
- **Explore with Grow**
- **Add to Canvas**

AI receives:

1. the safe equation object;
2. equation feature summary;
3. qualified module catalog;
4. current workspace context;
5. permitted geometric reasoning operations.

It does not receive authority to invent a module or execute arbitrary code.

An AI suggestion follows:

```text
equation
 -> structural features
 -> local AI/geometric ranker
 -> qualified module/edge selection
 -> graph validation
 -> preview
 -> user approval
 -> Canvas
```

## Grow

Grow may use an equation as a seed object.

Examples of bounded exploration:

- alter a parameter;
- compose with an approved transform;
- compare symmetry-related forms;
- apply a coordinate visualization;
- combine with another compatible object;
- propose a numerical derivative/residual experiment;
- propose a formally connected path when an actually qualified theorem binding
  exists.

Grow results remain ideas/proposals until executed and independently evaluated.

## Math on Canvas

An equation is a first-class Canvas object.

It may connect to:

- graphing modules;
- equation feature summaries;
- future symbolic transforms;
- numerical samplers;
- solver modules;
- geometric objects;
- AI/Grow proposal flows;
- proof-backed modules where the typed contract actually matches.

Equation cards should show the typeset expression prominently, with technical
metadata available on demand rather than dominating the visual design.

## Visual design principle

**Math first, machinery second.**

Default Canvas/UI presentation should favor:

- large readable mathematical notation;
- clear variable/unit labels;
- uncluttered graphs;
- subtle evidence/maturity indicators;
- expandable technical details.

Raw JSON, AST details, hashes and provenance remain available for reproducibility
but should not make ordinary mathematical work visually noisy.

## Security

The equation editor is data entry, not a code console.

The backend parser rejects code-like syntax and evaluates only the documented
mathematical allowlist.

Frontend parsing is convenience only. The Production CACE backend must parse and
validate the canonical equation again before execution.

## Qualification

The production Math Workspace is considered connected only after:

1. safe-parser rejection tests pass;
2. friendly-normalization tests pass;
3. canonical LaTeX/display tests pass;
4. explicit 2D graph regression passes;
5. implicit 2D contour regression passes;
6. explicit 3D surface regression passes;
7. capability-registry tests pass;
8. AI hidden-capability injection tests still pass;
9. browser math-editor and graph visual regressions pass;
10. frontend math dependencies, if any, pass license/SBOM review.
