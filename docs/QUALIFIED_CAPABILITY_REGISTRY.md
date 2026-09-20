# CACE-KSEE Qualified Capability Registry + Typed API Contract

Status: engineering/product contract. It is not mathematical proof evidence.

## Purpose

The engineering `ModuleRegistry` contains implemented, historical, experimental,
formal-bridge, research, and production-intended modules. That is useful for
development but unsafe as a product palette.

The **Qualified Capability Registry** is the fail-closed production exposure layer.

A module is hidden unless it is explicitly promoted through:

```text
implemented
  -> tested
  -> qualified_engineering
  -> registered
  -> ui_visible
  -> link_enabled
  -> ai_callable
```

Formal proof status is separate. Engineering capability qualification never
creates FORMAL/PASS or promotes a proof claim.

Canonical files:

- `ops/qualified_capabilities.json`
- `ops/capability_workflows.json`
- `cace_studio/core/capability_registry.py`
- `scripts/build_capability_manifest.py`

## Fail-closed rules

1. Existence in Python does not expose a module.
2. UI-visible modules must be explicitly listed and version-pinned.
3. Exposed modules require at least one executable regression workflow.
4. Link-enabled modules may only expose connection paths exercised by an approved
   workflow; type compatibility alone is insufficient.
5. Browser execution rejects hidden module IDs even if a client hand-crafts the
   request.
6. Local AI catalog/execution/canvas mutation uses the same capability registry.
7. Unknown or stale module versions fail registry construction.
8. Public Help is high-level: purpose, typed inputs/outputs, parameters, units,
   assumptions, limitations, evidence and examples. It does not expose
   proprietary implementation source or private algorithms.

## Initial production palette

The first intentionally small integration palette is:

- `core.constant`
- `core.add`
- `science.grid1d`
- `science.quadratic`
- `science.second_derivative`
- `verify.constant_residual`
- `verify.interval_literal`
- `verify.interval_square`

This is a bootstrap palette for connecting the product shell. It is not a claim
that other CACE modules are broken. Other modules remain engineering/research
capabilities until their complete user workflow is promoted.

## Initial qualified workflows

### Basic arithmetic

```text
Constant ----\
              -> Add -> sum
Constant ----/
```

### Quadratic curvature

```text
Grid 1D -> Quadratic Field --\
     \-----------------------> Centered Second Derivative
                                  -> Constant Residual Verifier
```

### Interval square

```text
Interval -> Interval Square
```

The exact graph fixtures and expectations live in
`ops/capability_workflows.json`.

## Browser API

Canonical boundary: `api/index.py`.

### `GET /api/capabilities`

Returns the production-safe capability catalog. Gemini should use this instead of
maintaining a static module list.

Important fields:

- policy hash;
- full engineering registry contract hash;
- typed ports/parameters;
- maturity and descriptive evidence metadata;
- capability gates;
- workflow IDs;
- safe public Help metadata;
- workflow-qualified compatible targets.

### `GET /api/capabilities/{module_id}`

Returns one UI-visible module contract.

### `GET /api/modules`

Compatibility endpoint. It is filtered to the same UI-visible capability set and
is deprecated in favor of `/api/capabilities`.

### `POST /api/connections/validate`

Authoritative connection validation.

A connection is valid only when:

- both modules are link-enabled;
- source/target ports exist;
- types/units are compatible;
- the exact edge pattern is qualified by a tested workflow.

### `POST /api/graphs/validate`

Validates a complete graph without executing it.

The browser should call this before a run and before treating a proposed graph as
ready.

### `POST /api/runs`

Runs only API-runnable qualified modules. Hidden module injection fails closed.

### Run status/control

Existing run endpoints remain:

- `GET /api/runs/{job_id}`
- `POST /api/runs/{job_id}/{pause|resume|cancel}`

## Local AI contract

When the local Tool Bus is constructed with the qualified capability registry:

- `cace.registry.list_modules` returns only AI-callable modules;
- `cace.experiment.run_active` rejects graphs containing hidden modules;
- canvas preview/plan mutation rejects insertion or retention of modules not
  allowed on the AI surface.

The AI never receives arbitrary module authority merely because it knows a module
ID.

## CI release manifest

Oracle CI/runner jobs execute the capability tests and then run:

```sh
python scripts/build_capability_manifest.py \
  --source-commit "$GITHUB_SHA" \
  --output cace-capability-manifest.json
```

The manifest binds:

- exact source commit;
- full engineering registry contract hash;
- capability-policy hash;
- workflow-contract hash;
- UI/link/AI/API module IDs;
- safe module contracts.

It is uploaded as CI engineering evidence.

This manifest means the capability exposure contract passed its engineering gates
for that exact source state. It does **not** mean every result is formally proved.

## Gemini rule

Gemini must:

- load capability state from the API;
- never render a hidden module;
- never invent compatible edges;
- never hard-code a static scientific module catalog;
- never reconstruct missing scientific semantics in TypeScript;
- render unknown capability/evidence states conservatively;
- use public Help metadata rather than source inspection for user-facing module
  documentation.

## Promotion of more modules

To promote another module:

1. confirm implementation exists;
2. add/directly strengthen unit/property/regression tests;
3. add a complete executable workflow;
4. add every intended connection edge to the tested workflow contract;
5. add high-level safe Help metadata;
6. add the module/version to the capability policy;
7. run cheap local/static tests;
8. let CI produce a new exact-head capability manifest;
9. deploy only the qualified release state.

No frontend-only promotion is allowed.
