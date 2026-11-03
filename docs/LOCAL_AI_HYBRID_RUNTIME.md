# CACE-KSEE Local Hybrid AI + Geometric Animation Runtime

Status: implementation contract. AI remains advisory and outside the scientific/
formal trusted computing base.

## Objective

CACE-KSEE should have a genuinely useful local research assistant that can:

- understand a research objective through a small local LLM;
- inspect only AI-callable qualified CACE capabilities;
- propose Minimal / Balanced / Exploratory experiment graphs;
- rank valid proposals with a tiny geometric neural model;
- preview and, after approval, set the experiment up on Canvas;
- observe active runs through bounded perception/heartbeat contracts;
- emit geometric reasoning actions as typed animation events;
- remain fully optional and support AI-OFF / local zero-contact operation.

The AI cannot create proof, promote evidence, invent modules, bypass graph validation,
or obtain arbitrary shell/network authority.

## Existing LLM layer

`cace_studio/ai/local.py` already provides loopback-only adapters for:

- Ollama;
- LM Studio;
- llama.cpp;
- OpenAI-compatible local servers.

The provider code rejects public-network endpoints and environment proxy routing.

This lets deployments choose a small quantized model appropriate to the user's
machine without hard-coding one vendor/model into CACE.

## Tiny geometric neural ranker

`cace_studio/ai/compact_geometric_ranker.py` provides a small NumPy MLP:

```text
12 -> 16 -> 8 -> 4 -> 1
```

Parameter count: **385**

Float32 parameter size: **1540 bytes** before model-container metadata.

This ranker is intentionally tiny. The local LLM handles language and candidate
generation. The neural component cheaply learns which already-valid candidates
are useful based on features such as:

- user relevance;
- tested workflow coverage;
- typed/link-qualified connection fraction;
- invariant-preserving/checker structure;
- symmetry reduction;
- geometric structure;
- novelty;
- mastery frontier;
- proof alignment as metadata only;
- resource headroom;
- sparsity;
- composition-depth fit.

It supports pairwise preference training.

## Geometric reasoning curriculum

Canonical existing training/evaluation material:

- `cace_studio/core/reasoning.py`
- `cace_studio/core/reasoning_curriculum.py`
- `docs/LOCAL_AI_REASONING_CURRICULUM.md`
- `docs/CACE_REASONING_OPERATOR_V1.md`
- `CACE_GRADED_GEOMETRY_ROADMAP.md`

The curriculum already includes exact/native-backed geometric/combinatorial
operations such as permutation actions, finite-group canonicalization, exterior
wedge structure, exact affine maps, and simplex/barycentric operations.

Preferred training pattern:

1. generate seeded baseline/intervention pairs;
2. hold out complete operator/composition families;
3. use native/exact CACE operators to generate expected mathematical behavior;
4. derive compact ranking features from the task/perception state;
5. train the tiny pairwise ranker to prefer useful, valid, sparse candidate plans;
6. evaluate transfer on held-out geometric/composition families;
7. never convert model confidence into evidence status.

This captures the earlier CACE geometric-reasoning direction: compress relational
structure into typed geometric/operator representations, exploit symmetry and
invariants, use sparse compositions and group actions, and evaluate whether those
representations reduce search while preserving useful behavior.

## Experiment suggestion and Canvas setup

`cace_studio/agent_runtime/experiment_advisor.py` implements the strict boundary:

```text
user objective
  -> local LLM strict JSON proposals
  -> Qualified Capability Registry
  -> workflow-qualified edge validation
  -> GraphExecutor validation
  -> compact neural ranking
  -> Minimal / Balanced / Exploratory proposals
  -> CanvasPreviewRequest
  -> user approval
  -> canonical canvas commit
```

A proposal is never applied directly from model text.

The advisor exposes only modules returned by the AI surface of the Qualified
Capability Registry. Hidden/unqualified module IDs or merely type-compatible but
untested connection paths are rejected.

## Geometric reasoning -> GUI animation

Canonical bridge:

- `cace_studio/core/geometric_animation.py`
- `ops/coordinate_views.json`
- `schema/cace-geometric-animation-event.schema.json`

When AI or a reasoning operator selects a point, transforms geometry, performs a
group action, follows a Grow/random-walk step, highlights a relation, or morphs a
structure, it should emit `GeometricActionEvent`.

The event records canonical geometry once.

The selected coordinate renderer receives a presentation projection of the same
event:

```text
canonical geometric action
        |
        +-> Cartesian
        +-> hex / Eisenstein lattice
        +-> complex-i
        +-> omega / Eisenstein complex
        +-> hierarchical quadtree fractal
        +-> Morton/Z-order fractal
        +-> complex radix 2i-1 fractal
        +-> complex radix omega-2 fractal
        +-> Einstein-hat aperiodic monotile
```

The semantic event hash does not include the selected coordinate view. Changing
the view can never change the experiment or evidence.

## Coordinate-view production gate

The view registry preserves all requested coordinate systems.

The production UI must still fail closed:

- a renderer with no implementation/test is not shown;
- Einstein/aperiodic and complex-radix/fractal views stay hidden until Gemini
  implements the actual renderer and visual regressions;
- presentation math must not be confused with a semantic coordinate transform;
- any transformation intended to change computation must be an explicit typed
  CACE module.

## Gemini / Antigravity implementation role

Gemini AI Code Studio / Antigravity should implement the browser presentation
pieces against these contracts:

1. local-AI setup/provider selection UX;
2. Research Assistant proposal cards;
3. Minimal / Balanced / Exploratory graph preview;
4. Build on Canvas approval flow;
5. geometric animation event consumer;
6. coordinate-view selector populated only by renderer-qualified views;
7. 2D/3D animation and camera interaction;
8. Einstein-hat tile renderer;
9. fractal/complex-radix renderers;
10. visual regression tests proving the same semantic event is rendered without
    changing its semantic hash.

Gemini must not reimplement the CACE scientific engine in JavaScript.

## Definition of "AI functional"

Do not label the local AI production-functional until all of these pass:

- loopback provider health/model selection;
- strict JSON planning;
- qualified capability filtering;
- hidden-module injection rejection;
- proposal graph validation;
- neural ranking;
- Canvas preview + approval + commit;
- recovery/reconnect behavior;
- animation event emission;
- browser event rendering;
- at least one end-to-end experiment constructed and run from an AI suggestion;
- AI-OFF mode remains fully functional.


## Matter, shape, and federated-city context

The local AI may also propose qualified geometric-object experiments from
`docs/MATTER_AND_SHAPE_TOOLBOX.md`.

This includes circles, parabolas, conics, hyperbolas, spheres, hypercubes,
element-labelled atoms, molecular graph construction, and affine transforms.

The AI must treat atom/molecule objects according to their declared geometric
scope. It may not invent force-field, orbital, reaction, energetic, or
quantum-chemistry claims.

When an authorized collaboration link connects two or more workspaces, the AI may
consume the bounded federated heartbeat/resource view defined in
`docs/CONWAY_ECONOMIC_CITY.md`.

The city may influence orchestration, complementary experiment suggestions,
resource scheduling, and animation, but never capability qualification,
verification state, proof promotion, permissions, payments, or real-money/crypto
authority.
