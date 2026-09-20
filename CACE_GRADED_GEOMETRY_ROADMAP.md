# CACE Graded Geometry / Geometric-Algebra Roadmap

Status: proof-first design plan.  No runtime-speed claim is trusted until separately benchmarked.
Branch target: `formal/low-cost-transform-combinatorics`.

## Goal

Compile long certified transform chains into smaller structure-preserving geometric objects while keeping
Lean as the trust boundary.  A planner/runtime may choose a compressed representation, but Lean must
prove that it has the same mathematical action and preserves the required invariants.

The intended dependency chain is:

```
CertifiedComposition
  -> ExteriorPowerTransport                  (#1)
  -> DualBladePiola                          (#2)
  -> CellBladeComplex                        (#3)
  -> GradedTransformCertificate              (#4)
  -> RotorNormalizer                         (#5)
  -> BoundaryBladeFusion                     (#6)
  -> SparseBladeKernel (C++ + verified spec) (#7)
  -> SpinorCache                             (#8)
  -> DiscreteRotorConnection / Holonomy      (#9)
```

## 1. Exterior-power / blade transport — FIRST

Initial exact scope is two-dimensional, matching the current certified affine/P1/RT0 stack.

Represent the exterior grades without importing a large opaque runtime abstraction:

- grade 0: scalar;
- grade 1: vector / oriented edge;
- grade 2: signed bivector coefficient / oriented area.

Core theorems:

- `wedge2 (A u) (A v) = det(A) * wedge2 u v`;
- grade-1 action respects affine-linear composition;
- grade-2 action respects composition;
- edge vectors remove translation exactly;
- triangle determinant is the wedge of its two edge vectors;
- arbitrary affine chains collapse grade-by-grade.

This becomes the small trusted algebraic specification that later generic/n-dimensional exterior
implementations must refine.

## 2. Dual-blade Piola unification — FIRST

Use the 2D Hodge/quarter-turn dual to unify tangent blades, normal-measure vectors, cofactors, and
contravariant Piola flux.

Core theorems:

- `dual (A t) = cof(A) (dual t)`;
- for arbitrary normals,
  `cof(A) n = dual (A (dualInv n))`;
- cofactor actions compose exactly;
- Piola actions compose for nonsingular stages;
- transformed oriented edge-normal measure is the cofactor image of the original;
- Piola/cofactor flux conservation is exposed as a dual-blade theorem.

This should become the canonical bridge used by the existing affine P1/RT0 transport layer.

## 3. Cell–blade complex

Pair exact mesh topology with local oriented geometry:

`CertifiedKCell = (cell id, incidence/boundary data, k-blade geometry)`.

Targets:

- boundary operator remains integer/topological;
- geometry is transported by the matching exterior grade;
- prove a commuting law `boundary (F# cell) = F# (boundary cell)`;
- derive interior-face orientation cancellation from topology + blade orientation.

## 4. Graded Transform Certificate

One certificate stores a fused affine/graded action and its proof provenance:

- translation;
- grade-1 action;
- grade-2/top-grade action;
- determinant/orientation;
- optional cofactor/Piola action;
- static cost metadata;
- theorem/provenance identifiers.

Prove that a 5–9+ primitive transform chain can compile to one certificate with identical action.

## 5. Rotor normalizer

Recognize exact orthogonal subchains only.

- represent exact rotations/reflections with an orthogonal/versor certificate;
- collapse maximal orthogonal subchains;
- prove equivalence with the corresponding grade-1 and grade-2 affine actions;
- never encode shear or anisotropic scale as an ordinary rotor.

Numerical polar decomposition is a later certified-numerics task, not part of the first trust-bearing
implementation.

## 6. Boundary-blade fusion

Reuse one transformed exterior ladder to provide:

- transformed edges;
- oriented face/area data;
- determinant/volume factor;
- normal-measure/cofactor data;
- Piola flux geometry.

Goal: eliminate duplicate geometry calculations and duplicate proof obligations.

## 7. Sparse C++ blade kernel

After the Lean specification is stable:

- basis blades encoded by bit masks;
- grade by popcount;
- zero-wedge detection by bit intersection;
- sign from permutation parity;
- fixed-size specialization for low dimensions;
- SIMD/GPU candidates only after benchmarks.

The C++ kernel is an implementation of a Lean-specified operation, never part of the proof trust
boundary by itself.

## 8. Spinor cache

Canonicalize repeated orientation-preserving rotor chains in the even Clifford algebra.

Requirements:

- handle the `R ~ -R` double-cover equivalence explicitly;
- cache by canonical mathematical action, not floating-point byte pattern;
- preserve exact/certified route when input generators are exact;
- useful for repeated frames, physics modules, and high-dimensional rotations.

## 9. Discrete rotor connection / holonomy

Attach certified relative frame transforms to neighboring cells.

Targets:

- edge/face transition rotor or versor;
- path composition;
- loop holonomy certificate;
- flatness/curvature diagnostics;
- compatibility with k-cell incidence and exterior transport.

This is exploratory until the exact algebraic semantics are proved.

## Proof / performance policy

1. Mathematical identities are proved in Lean.
2. Generated plans and rankings stay outside the theorem kernel.
3. Runtime compression must have a theorem equating it to the uncompressed transform chain.
4. Static-cost metadata is not a wall-clock claim.
5. Performance claims require reproducible benchmarks against matrix/quaternion/baseline kernels.
6. Exact-current-head compilation, axiom audit, theorem metadata, and canonical qualification are
   required before a new proof layer is promoted.

## Current implementation order

- [x] #1 ExteriorPowerTransport
- [x] #2 DualBladePiola
- [ ] #3 CellBladeComplex
- [ ] #4 GradedTransformCertificate
- [ ] #5 RotorNormalizer
- [ ] #6 BoundaryBladeFusion
- [ ] #7 SparseBladeKernel
- [ ] #8 SpinorCache
- [ ] #9 DiscreteRotorConnection

After #1 and #2 are structurally complete, return to the remaining proof-critical items:
unconditional H(div) regularization/density, standard bounded-domain identifications where needed,
concrete continuum Prager–Synge instantiation, weighted SPD energy, audit/metadata enrollment, and
canonical exact-current-head qualification.


## Implemented in this branch

### #1 ExteriorPowerTransport

File: `formal/cace_formal/CACEFormal/ExteriorPowerTransport.lean`

Implemented exact 2D grade-0/1/2 semantics, wedge/determinant transport, translation-free edge
vectors, triangle determinant as a 2-blade, and arbitrary-chain grade-1/grade-2 fusion.

### #2 DualBladePiola

File: `formal/cace_formal/CACEFormal/DualBladePiola.lean`

Implemented 2D dual/Hodge transport, cofactor-as-dual-conjugated-grade1, cofactor composition,
edge normal-measure transport, Piola composition for nonsingular chains, and dual-blade flux
conservation.


## Combinatorial/group action bridge

The graded-geometry stack should interoperate with the exact combinatorics/group-action toolbox rather than treating geometric transforms as unrelated one-off formulas.

Target path:

```text
finite combinatorial/group object
 -> certified action / canonical representative
 -> cell/vector/frame/blade transformation
 -> invariant/equivariance checker
 -> fused graded certificate/kernel
 -> Local-AI ReasoningOperator
```

High-value exact interfaces include:

- permutations of vertices/cells/basis blades;
- orientation/sign actions;
- finite symmetry groups of supported meshes/shapes;
- orbits of equivalent cell/frame configurations;
- canonical representatives for cache/reasoning reuse;
- composition/inverse of supported transform actions.

This is expected to reduce repeated equivalent work only when benchmarked. The group representation and its action must be explicit and checked; visual symmetry alone is not enough.
