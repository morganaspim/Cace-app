# CACE Proof-Backed Math Toolbox Roadmap

Status: implementation roadmap. **Not proof evidence.**

## Goal

Build a broad mathematical toolbox around RMK-v1, prioritizing tools whose assumptions and identities can be checked exactly or connected to Lean proofs.

The objective is not “the largest module count.” It is the largest useful set of **canonical, composable, truthful mathematical tools**.

## Module evidence badge model

Every math module should display one or more badges:

- FORMAL — current qualified theorem connection for the exact claim;
- EXACT — deterministic exact checker/certificate;
- INTERVAL — rigorous enclosure;
- SYMBOLIC — deterministic symbolic identity/check;
- NUMERICAL — floating computation/diagnostic;
- REVIEWED — mathematical theorem imported with explicit assumptions but not machine-formalized;
- EXPERIMENTAL — research behavior.

FORMAL is never inferred from REVIEWED or EXACT.

## Priority families

### Tier A — core algebra

1. integer arithmetic
2. rational arithmetic
3. complex arithmetic
4. Gaussian/Eisenstein integer tools
5. vector operations
6. matrix operations
7. sparse matrices
8. determinant
9. rank
10. RREF
11. nullspace
12. exact linear solve
13. linear map composition
14. basis/change-of-basis
15. tensor/Kronecker product
16. quadratic/bilinear forms

Proof opportunities:
- algebraic identities;
- determinant/orientation lemmas;
- inverse/solve checker correctness;
- composition laws.

### Tier B — polynomial and symbolic calculus

17. sparse polynomial construction
18. simplify/canonicalize polynomial
19. exact polynomial equality
20. derivative
21. gradient
22. Jacobian
23. Hessian
24. divergence
25. curl
26. Laplacian
27. directional derivative
28. Taylor polynomial + remainder contract
29. root verification/certified enclosure
30. polynomial interpolation

Proof opportunities:
- derivative identities;
- composition/chain rules in bounded supported scope;
- polynomial reproduction;
- exact interpolation identities.

### Tier C — geometry

31. point/vector/frame
32. affine transform
33. simplex construction
34. barycentric coordinates
35. orientation/signed volume
36. distance/angle
37. line/plane/hyperplane
38. intersections with exact predicates
39. convex combination
40. convex hull checker
41. polygon/polytope incidence
42. mesh topology
43. face orientation
44. coordinate transforms
45. lattice coordinates
46. exterior k-vector/blade
47. wedge product
48. dual/Hodge operation
49. rotor
50. geometric transform composition

Proof opportunities:
- existing affine geometry;
- exterior/Piola transport;
- mesh combinatorics;
- certified composition.

### Tier D — number theory and combinatorics

51. gcd/lcm
52. extended Euclid
53. modular arithmetic
54. CRT checker
55. primality certificate verifier
56. rational reconstruction
57. continued fractions
58. permutations
59. combinations
60. finite groups (small explicit)
61. graph adjacency/incidence
62. connected components
63. spanning tree checker
64. DAG/topological order
65. Cantor pairing/unpairing
66. exact finite counting identities

Formalization priority should follow reuse and tractability rather than attempting all of number theory at once.

### Tier E — analysis and inequalities

67. norm calculators
68. inner products
69. Cauchy-Schwarz checker/instance
70. triangle inequality instance
71. weighted energy
72. Rayleigh quotient
73. residual spectral bound
74. interval extrema
75. Lipschitz bound checker
76. contraction mapping certificate for explicit finite/numeric maps
77. fixed-point residual diagnostics
78. quadrature rules + exactness checks
79. interpolation error contracts
80. conditioning diagnostics

Existing reviewed modules for Lax-Milgram, Céa, Bramble-Hilbert, Aubin-Nitsche, estimator efficiency, adaptivity, inverse inequalities, DMP and FEEC should be migrated to canonical names and remain REVIEWED unless formally connected.

### Tier F — differential equations / variational math primitives

81. ODE RHS/operator
82. explicit integrator
83. implicit residual form
84. weak form object
85. bilinear form
86. linear functional
87. coercivity/continuity evidence record
88. boundary-condition object
89. residual
90. energy norm
91. local balance
92. flux object
93. exact affine FE field
94. trace/jump/average
95. Green identity checker
96. discrete orthogonality
97. hypercircle/Prager-Synge exact instance
98. estimator/certificate composition
99. refinement map
100. proof-obligation collector

### Tier G — topology / functional-analysis bridges

These should expose qualified formal results carefully and not pretend runtime finite arrays are automatically continuum objects.

101. graph-space descriptor
102. H1 premise record
103. H(div) premise record
104. weak derivative premise
105. normal-trace premise
106. zero-boundary premise
107. density/closure obligation
108. volume pairing
109. weak Green obligation
110. orthogonality obligation
111. Prager-Synge premise graph
112. source-to-formal binding certificate

These are primarily proof/evidence orchestration modules until concrete runtime embeddings are proved.

### Tier H — transforms and applied mathematical utilities

113. FFT/DFT
114. convolution
115. finite differences
116. finite volume operators
117. interpolation/resampling
118. coordinate transforms
119. rotations
120. rigid transforms
121. graph Laplacian
122. sparse operators
123. projection
124. least squares
125. SVD numerical diagnostic
126. eigen solve + residual certificate
127. optimization objective/gradient
128. constrained projection
129. Monte Carlo sampler
130. deterministic quadrature/cubature

## Proof-first expansion strategy

For each existing Lean theorem family:

1. identify a useful user-facing mathematical operation;
2. define a canonical runtime object matching the theorem's actual hypotheses;
3. expose unresolved premises rather than hiding them;
4. add exact checker/certificate when possible;
5. add source-to-formal bridge only when representation identity is explicit;
6. promote FORMAL only after canonical qualification.

This converts the proof corpus into tools rather than leaving proofs isolated in a Proof Explorer.

## High-leverage existing Lean -> module mappings

Candidate mappings:

- `AffineGeometry` -> affine map / simplex orientation / coordinate modules
- `ExecutableRationalGeometry` -> exact rational geometry
- `CertifiedComposition` -> certified map composition
- `ExteriorPowerTransport` + `DualBladePiola` -> k-vector / exterior / Piola transform tools
- `MeshCertificate` + `MeshCombinatorics` -> mesh validity/topology tools
- `P1RT0Element` -> exact P1/RT0 cell tools
- `MeshFaceAssembly` + `RT0P1DerivedAssembly` -> exact global assembly tools
- `DiscreteOrthogonality` -> orthogonality certificate
- `DiscretePragerSynge` -> exact discrete hypercircle tool
- `GraphGreenPairing` / `WeakGreenFunctional` -> premise/obligation tools
- `BoxNormalTrace` / `BoxGraphTrace` -> normal-trace tools
- `WeightedEnergy` -> weighted energy/norm tool

Actual FORMAL status must come from the canonical proof gate.

## Canonical module naming

Prefer semantic IDs such as:

- `math.exact.rational`
- `math.linalg.exact_solve`
- `math.geometry.simplex`
- `math.calculus.gradient`
- `math.exterior.wedge`
- `math.fem.p1_affine`
- `math.fem.rt0_affine`
- `math.proof.green_identity`

Avoid new product-version IDs such as `math_v126.py` unless required only as temporary compatibility adapters.

## Help requirement

Every production-intended math module must have:
- one-sentence purpose;
- mathematical definition/formula;
- input/output table;
- assumptions;
- evidence badge explanation;
- limitations;
- at least one tiny worked example;
- at least one runnable CACE graph example;
- “connects well with” suggestions.

## Definition of a strong math toolbox

A strong toolbox is reached when users can build meaningful mathematical pipelines without custom code, and each node states exactly what it computes and how strongly it is justified.


## Combinatorial/group reasoning expansion

Tier D is also a high-leverage AI reasoning substrate.

Expand the canonical exact toolbox, in bounded tractable scope, toward:

- permutation groups and composition;
- finite explicit groups;
- generators/relations for supported small classes;
- group actions;
- orbits/stabilizers;
- canonical representatives;
- small-group Cayley graphs/tables;
- exact symmetry/invariance checks;
- incidence/boundary combinatorics;
- rewrite/normal-form systems.

Connect these operations to the graded/geometry stack so group actions may operate on supported vectors, frames, cells, blades and graphs through explicit typed maps.

Each accepted operation should be eligible to become a Local-AI `ReasoningOperator` with preconditions, invariants, inverse/composition metadata and linked exact/formal checkers.

The intended benefit is not abstract module count. Canonical group structure can collapse symmetry-equivalent search states and turn long reasoning sequences into reusable operator compositions. Performance/efficiency claims require benchmarks.

## Experiment-to-proof tool feedback

The toolbox should consume reusable qualified results discovered through `docs/EXPERIMENT_TO_PROOF_DISCOVERY_LOOP.md`.

A successful new proof should be assessed for whether it deserves:
- a canonical user-facing operation;
- an exact checker;
- a C++ kernel;
- a canvas module;
- a ReasoningOperator;
- structured Help/examples.

This is how the proof corpus becomes an increasingly useful computational/reasoning library rather than a disconnected archive.
