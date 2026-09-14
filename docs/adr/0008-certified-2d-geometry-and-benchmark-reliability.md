# ADR 0008 — Certified 2D geometry and scoped reliability (v0.6)

## Decision
v0.6 extends CACE's rigorous FEM layer to counter-clockwise 2D triangular meshes. Stored binary64 vertex coordinates are treated as the exact input geometry. Derived Jacobians, determinants, areas, inverse-transposes, P1 gradients, edge lengths, inradii, shape ratios, and local stiffness entries are outward-enclosed with interval arithmetic.

The first 2D continuum certificate is deliberately benchmark-scoped to the reference triangle with

- `u(x,y)=x*y*(1-x-y)`,
- `-Δu=2(x+y)`,
- homogeneous Dirichlet data on `x=0`, `y=0`, and `x+y=1`.

For this manufactured solution, the energy error of the actually computed P1 function is enclosed by exact polynomial pullback integration on each affine triangle. A residual/jump estimator is independently interval-enclosed. CACE may certify `E <= C_rel η` for that particular run when the two intervals establish it.

## Non-decision
v0.6 does **not** claim that the same `C_rel` is valid for arbitrary meshes, domains, coefficients, or forcing. The mesh-uniform 2D reliability theorem remains a formal obligation and reports `NOT_RUN`.

## Refusal behavior
A triangle is rejected if its interval determinant contains zero or if its orientation is not provably counter-clockwise. Shape-regularity threshold failure is `NOT_RUN`, not `PASS`. Missing CUDA produces `NOT_RUN` for CPU↔GPU equivalence.
