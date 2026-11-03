# CACE Science Module Completeness and Interoperability Standard

Status: product/engineering specification. **Not scientific evidence.**

## 1. Goal

After RMK-v1 and the canonical Math Toolbox are stable enough, CACE should systematically upgrade science modules from isolated demonstrations into full-featured, composable scientific building blocks.

Every scientific domain should be able to reuse the same math, units, geometry, fields, solvers, evidence and visualization contracts.

## 2. Definition of a full-featured science module

A production-intended science module must provide:

### Identity
- stable semantic module ID;
- semantic version;
- domain/category;
- maturity;
- source/license/provenance where external data is used.

### Typed interfaces
- typed input ports;
- typed output ports;
- canonical units/dimensions;
- shape/dimension constraints;
- optional uncertainty/error representation where relevant.

### Assumptions
- mathematical assumptions;
- physical assumptions;
- numerical assumptions;
- domain of validity;
- explicit nonclaims.

### Execution
- deterministic behavior where feasible;
- seed control for stochastic behavior;
- CPU implementation;
- optional C++/GPU implementation only where justified;
- resource bounds.

### Verification
At least one appropriate verifier:
- exact checker;
- interval certificate;
- conservation law;
- invariant;
- residual;
- convergence check;
- cross-method check;
- reference solution;
- formal theorem linkage;
- explicit NOT_RUN when unavailable.

### Interoperability
- consumes canonical shared object types;
- produces reusable canonical object types;
- avoids domain-specific duplicate representations;
- declares compatible upstream/downstream modules.

### Reproducibility
- serializable parameters/inputs;
- semantic fingerprint;
- backend identity;
- dependency identity;
- result provenance.

### Documentation
- Help page;
- equations/model definition;
- assumptions/limitations;
- citations/reference sources where appropriate;
- at least one beginner example;
- at least one compositional example;
- troubleshooting/failure explanations.

## 3. Canonical shared science object families

Science modules should converge on shared types rather than bespoke dictionaries:

- scalar/vector/tensor;
- time series;
- sampled field;
- mesh;
- geometry/body;
- material;
- particle/system state;
- molecule;
- protein sequence/structure;
- boundary condition;
- source/load;
- operator;
- linear/nonlinear system;
- solution field;
- residual;
- certificate/evidence;
- units/dimensions;
- uncertainty/enclosure.

## 4. Linking rules

A useful CACE canvas should support chains such as:

```text
Geometry -> Mesh -> Material -> PDE -> Solver -> Residual -> Estimator -> Certificate -> Plot
```

```text
Molecule -> Geometry -> Potential -> Optimizer -> Spectrum/Property -> Uncertainty -> Report
```

```text
Protein Structure -> Geometry/Graph -> Energy/Descriptor -> Search -> Compare -> Visualization
```

```text
Particle System -> Force Law -> Integrator -> Conserved Quantity Audit -> Trajectory -> Plot
```

```text
Dataset -> Transform -> Statistical Model -> Residual/Uncertainty -> Hypothesis/Diagnostic -> Report
```

Modules should connect because of typed shared objects, not because the UI special-cases pairs of module names.

## 5. Science domain upgrade order

### S1 — numerical/physical foundations
- units/dimensional quantities;
- constants;
- grids;
- interpolation;
- differentiation;
- integration;
- ODE solvers;
- linear/nonlinear solves;
- uncertainty basics.

### S2 — mechanics
- particles;
- rigid bodies;
- force fields;
- energy/momentum;
- oscillators;
- orbital mechanics;
- continuum mechanics primitives.

### S3 — PDE/FEM
- Poisson/diffusion;
- heat/parabolic;
- elasticity;
- Stokes/Navier-Stokes research tooling;
- Maxwell/electromagnetics;
- Helmholtz/waves;
- DG/SUPG variants;
- certified estimators.

### S4 — electromagnetism / fields
- scalar/vector fields;
- charge/current;
- E/B fields;
- potentials;
- Maxwell operator blocks;
- flux/circulation diagnostics.

### S5 — chemistry / molecular
- atoms/bonds/molecules;
- molecular geometry;
- descriptors;
- safe reactions/data workflows;
- potential/energy models;
- structure import.

### S6 — materials
- composition/crystal/lattice descriptors;
- elasticity/thermal/electrical properties;
- screening;
- uncertainty;
- FEM coupling.

### S7 — proteins / biophysics
- sequence;
- structure import;
- residue graphs;
- geometry;
- low-cost energy/search;
- comparison/alignment;
- confidence/provenance.

### S8 — statistics / data science
- distributions;
- descriptive statistics;
- regression;
- uncertainty;
- sampling;
- Bayesian building blocks where implemented rigorously;
- time-series tools.

### S9 — signals / systems
- FFT/spectra;
- filters;
- convolution;
- transfer functions;
- state-space;
- stability diagnostics.

### S10 — quantum / research physics
- finite-dimensional quantum states/operators;
- unitary evolution;
- small exact/numerical systems;
- clearly labeled experimental/research models.

## 6. Help Center architecture

Every registered module should be able to expose structured help metadata.

Recommended canonical help object:

```text
ModuleHelp
  summary
  theory
  equations
  inputs
  outputs
  parameters
  units
  assumptions
  evidence
  limitations
  examples[]
  connects_well_with[]
  references[]
  troubleshooting[]
```

The Help UI should support:
- “What does this do?”
- “What math/science is behind it?”
- “What assumptions must hold?”
- “How strong is the evidence?”
- “Show a tiny example.”
- “Add example to Canvas.”
- “What can I connect next?”
- “Why did verification fail?”

## 7. Example contract

Each production-intended module should have at least:

1. **Minimal example** — smallest understandable graph.
2. **Realistic example** — representative use.
3. **Composition example** — linked to at least two other modules where meaningful.
4. **Failure example** — demonstrates a violated assumption or verifier failure for high-value/safety-critical modules.

Example files should be executable, versioned and tested.

Long-term target remains ~100 curated high-value examples, but quality/composability is more important than count.

## 8. Interdisciplinary example targets

High-value showcase graphs:

- certified Poisson solve -> equilibrated flux -> error bound;
- elasticity -> material properties -> stress field -> verification;
- EM mesh -> Maxwell operator -> field solve -> energy/flux;
- molecule -> geometry -> material descriptor -> screening;
- protein structure -> residue graph -> geometry descriptors -> search/compare;
- oscillator -> ODE solver -> energy conservation audit;
- signal -> FFT -> filter -> inverse transform -> error diagnostic;
- geometric algebra rotor -> rigid-body transform -> visualization;
- exact mesh/P1/RT0 -> discrete Green -> Prager-Synge certificate.

## 9. Migration rule for current modules

Do not delete historical/versioned modules abruptly.

For each domain:
1. inventory current module IDs;
2. identify canonical capabilities;
3. implement stable canonical modules;
4. add adapters/aliases where needed;
5. migrate examples/tests;
6. mark superseded wrappers deprecated;
7. remove only after a documented compatibility window.

## 10. Definition of done for a domain

A science domain is “full-featured” only when:

- core workflows can be built by connecting modules;
- shared types/units work across module boundaries;
- at least one meaningful verification path exists for important outputs;
- Help pages explain assumptions and evidence;
- runnable examples exist;
- failure states are understandable;
- no browser-only semantic implementation is required;
- the domain passes its regression suite.


## 11. Production-grade means end-to-end complete

A module or domain is not production-grade merely because its core algorithm exists.

For every advertised production workflow, CACE must validate the whole path:

```text
discover/select
 -> wizard/typed input
 -> connect compatible modules
 -> validate types/units/domains/assumptions
 -> execute
 -> verify/certify where applicable
 -> inspect results/evidence
 -> save/replay/export
 -> Help/troubleshooting
 -> representative regression test
```

Required UI/API/CLI/agent paths must share the same semantics.

No production badge for a module/domain while a required step is a placeholder, silently unsupported, duplicated only in browser code, or unable to round-trip through persistence.

Cross-module end-to-end regression graphs are mandatory for production domains.

## 12. Input wizard requirement

Modules with nontrivial equations, data schemas, boundary/initial conditions, material definitions or other structured inputs should integrate with `docs/TYPED_EQUATION_DATA_WIZARD.md`.

The wizard is part of module completeness when ordinary users would otherwise need internal syntax or undocumented conventions.

## 13. Experiment-to-proof integration

Suitable science modules should expose exact identities, invariants, residual relations, symmetry structure and theorem applicability metadata to the proof-discovery layer defined in `docs/EXPERIMENT_TO_PROOF_DISCOVERY_LOOP.md`.

This supports proof discovery without turning empirical behavior into proof.


## Production language-primitive gate

A production module must work as a real typed language primitive on the CACE
canvas, not only as an isolated demo card.

Required behavior:

```text
discover
 -> understand
 -> typed input/wizard
 -> connect through canonical ports
 -> validate
 -> execute
 -> verify
 -> inspect/animate
 -> persist/replay
 -> compose into reusable subgraph
 -> Help/demo
 -> recover from failure
```

Representative end-to-end chains must be regression-tested. A module is not
production-grade when its neighboring connections are placeholders, its data
must be manually retyped into a bespoke representation, or the browser
implements special-case scientific semantics that the API/core does not share.

Reusable subgraphs should be promotable to higher-level modules with explicit
input/output contracts so the canvas increasingly behaves like an intuitive
scientific programming language.


## Public Help / proprietary boundary

User-facing Help is a contract view, not a source-code browser.

For each production-visible module, public Help should explain:

- purpose;
- typed inputs and required/optional status;
- typed outputs;
- units/dimensions;
- parameters;
- assumptions and validity domain;
- evidence/maturity;
- limitations/nonclaims;
- compatible workflow-qualified neighbors;
- minimal, compositional, and failure examples;
- troubleshooting.

Public Help must not disclose proprietary implementation source, private algorithms,
internal proof-search strategies, protected native-core details, private API
internals, security bypass details, or internal heuristics merely to explain how a
module works.

Gemini should consume the safe public-help metadata supplied by the Qualified
Capability Registry rather than scrape protected source for user documentation.
