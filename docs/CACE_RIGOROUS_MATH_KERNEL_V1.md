# CACE Rigorous Math Kernel v1

Status: architecture and implementation specification. **Not proof or qualification evidence.**

## 1. Purpose

CACE Rigorous Math Kernel v1 (RMK-v1) is the shared mathematical substrate for proof-backed math tools and composable science modules.

It should replace the pattern of many isolated/versioned helper implementations with a small set of canonical, typed, reusable primitives.

Target dependency direction:

```text
Science modules / Math toolbox / GUI
            |
            v
     typed Python orchestration
            |
            v
      C++ Rigorous Math Kernel
            |
      +-----+----------------+
      |                      |
      v                      v
 exact/certified checks   source-to-formal binding
                             |
                             v
                         Lean proofs
```

Python orchestrates. Load-bearing exact/high-performance mathematics lives in C++. Lean remains the formal source. Browser code consumes API results and never becomes a mathematical authority.

## 2. Evidence modes

Every RMK operation must declare one of these modes, and callers must not silently upgrade between them:

1. **exact** — integer/rational/algebraic data with exact equality;
2. **interval-certified** — outward-rounded enclosure with explicit containment claim;
3. **symbolic/checker-backed** — deterministic symbolic identity/checker result;
4. **numerical** — floating-point computation with diagnostics/tolerances;
5. **formally connected** — exact runtime object explicitly bound to a qualified Lean theorem endpoint.

A single operation may expose several implementations, but each result records which path actually ran.

## 3. RMK-v1 canonical primitive families

### R1 — Exact scalar arithmetic

Required:
- signed integers;
- normalized exact rationals;
- checked add/subtract/multiply/divide;
- GCD normalization;
- exact comparison/order;
- checked conversion boundaries;
- fail-closed overflow/resource policy;
- deterministic text/binary serialization.

Future-compatible extension points:
- arbitrary-precision integers/rationals;
- exact algebraic numbers;
- Gaussian/Eisenstein integers.

### R2 — Exact dense/sparse vectors and matrices

Required:
- fixed/dynamic vectors;
- dense and CSR/COO sparse matrices;
- exact dot product;
- matrix-vector/matrix-matrix products;
- transpose;
- exact row/column permutations;
- exact norms where meaningful;
- deterministic sparse canonicalization;
- structural hashes.

### R3 — Exact linear algebra

Initial exact tools:
- determinant;
- rank over Q;
- RREF;
- exact nullspace;
- exact linear solve when nonsingular;
- exact verification of a proposed inverse/solution;
- positive/negative definiteness checks for small exact matrices where decidable by implemented criterion.

Numerical/certified companions:
- residual;
- condition estimate;
- interval enclosure of solve/eigen quantities.

### R4 — Polynomial and affine algebra

Required:
- univariate/multivariate monomials and sparse polynomials;
- affine maps;
- polynomial evaluation;
- derivative/gradient/Hessian;
- exact composition;
- polynomial identity checking after canonical normalization;
- degree and support metadata.

This is a base for FEM shape functions, symbolic calculus, geometry and scientific constitutive models.

### R5 — Geometry primitives

Required:
- points/vectors in arbitrary finite dimension;
- affine frames;
- oriented simplex;
- barycentric coordinates;
- exact signed volume/Jacobian;
- edges/faces/cells;
- incidence/orientation data;
- exact affine transforms;
- change of basis;
- metric/signature metadata.

### R6 — Exterior / geometric algebra foundation

Required v1 scope:
- k-vectors/blades;
- wedge product;
- grade projection;
- contraction;
- pseudoscalar/orientation;
- Hodge-style dual where metric/orientation prerequisites are explicit;
- simple rotor representation for Euclidean rotations;
- exact algebraic identities on exact inputs where feasible.

Later:
- full Clifford products;
- spinors;
- PGA/CGA;
- sparse multivectors;
- k-cell/combinatorial encodings.

### R7 — Calculus operators

Canonical operator vocabulary:
- derivative;
- gradient;
- divergence;
- curl where dimension/convention supports it;
- Jacobian;
- Hessian;
- Laplacian;
- directional derivative.

Each operator must distinguish:
- symbolic exact action;
- discrete numerical approximation;
- weak/distributional meaning.

Do not represent these as one overloaded unchecked operation.

### R8 — Piecewise fields and interfaces

Required:
- cellwise affine/polynomial scalar/vector fields;
- mesh attachment;
- traces;
- oriented face normals;
- jumps/averages;
- normal/tangential components;
- cellwise divergence/gradient;
- interface cancellation records;
- deterministic global assembly.

This family is the direct bridge toward P1/RT0, DG, H1 and H(div) tooling.

### R9 — Functional/norm primitives

Initial:
- exact finite sums;
- dot/energy pairings;
- L1/L2/discrete lp norms;
- weighted quadratic energies;
- residual norms;
- exact/interval bounds when inputs permit.

Continuum Sobolev/H1/H(div) objects remain formal/analytic constructions, not mere runtime labels.

### R10 — Canonical mathematical packet

Every exact RMK object intended for proof linkage must support:
- schema/version;
- mathematical type ID;
- canonical serialization;
- semantic SHA-256;
- exact input representation;
- convention IDs (orientation, basis, units, metric, element family);
- source module/version;
- dependency object hashes.

This should align with FSL-0..FSL-7 in `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md`.

## 4. Proof linkage model

A proof-backed RMK operation has four separate layers:

```text
runtime exact computation
      ↓
deterministic checker/certificate
      ↓
runtime-to-Lean object binding
      ↓
qualified Lean theorem endpoint
```

No layer substitutes for another.

A module may say “exactly checked” without being “formally verified” if the source-to-formal binding or current-head qualification is absent.

## 5. Initial Lean reuse targets

Prefer reusing and exposing already-existing formal work instead of proving duplicates.

High-value existing formal families include:

- affine/reference geometry;
- rational/executable geometry;
- P1/RT0 elements;
- mesh certificates and combinatorics;
- face assembly;
- Piola/exterior transport;
- discrete orthogonality and Prager-Synge;
- graph spaces;
- H1/H(div) closure/density infrastructure;
- Green pairings and weak Green identities;
- normal trace;
- continuum orthogonality / Prager-Synge;
- weighted energy;
- certified composition.

Formal status must be read from canonical claim/proof data and exact qualification evidence, not inferred from a file existing.

## 6. C++ organization target

Preferred canonical layout:

```text
cpp/include/cace/math/
    rational.hpp
    vector.hpp
    sparse_matrix.hpp
    exact_linalg.hpp
    polynomial.hpp
    affine.hpp
    geometry.hpp
    exterior.hpp
    calculus.hpp
    piecewise.hpp
    norms.hpp
    packet.hpp

cpp/src/math/
cpp/tests/math/
```

Avoid one header per historical product version. Version APIs semantically rather than cloning implementation trees.

## 7. Python boundary

Python should expose typed wrappers and module contracts, not duplicate algorithms.

Preferred shape:

```text
cace_studio/math/
    types.py
    native.py
    packets.py
    evidence.py

cace_studio/modules/math/
    exact_arithmetic.py
    linear_algebra.py
    geometry.py
    calculus.py
    piecewise.py
    proof_backed.py
```

Historical `math_v102...` and similar modules should be progressively mapped to canonical module IDs, with compatibility aliases only where needed.

## 8. RMK-v1 implementation batches

### RMK-1 — exact scalar + vector + packet core
- rational;
- exact vector;
- canonical serialization/hashing;
- malformed/overflow tests.

### RMK-2 — sparse matrix + exact linear algebra
- sparse canonicalization;
- exact matvec/matmul;
- determinant/rank/RREF/nullspace/solve;
- property/adversarial tests.

### RMK-3 — polynomial + affine + geometry
- exact polynomials;
- derivatives;
- affine transforms;
- simplex orientation/Jacobians/barycentric coordinates.

### RMK-4 — exterior/graded primitives
- blades/k-vectors;
- wedge/dual/contraction;
- rotor primitives;
- exact identity checks.

### RMK-5 — piecewise fields + interface algebra
- cellwise polynomial fields;
- traces/jumps;
- oriented face terms;
- assembly/cancellation.

### RMK-6 — formal packet/binding hooks
- FSL-compatible packet;
- generated Lean literal path;
- exact source binding;
- fail-closed proof linkage metadata.

## 9. Acceptance criteria

RMK-v1 is ready for broad module adoption when:

- canonical C++ primitive APIs exist;
- Python is thin orchestration/binding;
- exact operations are deterministic across platforms;
- malformed/overflow cases fail closed;
- all exact objects have canonical semantic identity;
- evidence classes are explicit;
- proof-linked operations cannot claim formal PASS without exact binding + qualification;
- legacy math modules can be expressed as compositions of canonical primitives;
- science modules can consume the same typed objects without custom conversions.

## 10. Nonclaims

RMK-v1 does not make all mathematical operations formal.

A broad math library may contain exact, interval, numerical, reviewed, and formally connected tools side-by-side. The UI/help system must show the difference.
