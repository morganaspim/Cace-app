# ADR 0007 — First continuum FEM certificate is a scoped 1D theorem

## Status
Accepted for v0.5.

## Decision
CACE v0.5 will not claim a generic residual-estimator reliability theorem in arbitrary dimension. The first continuum-level certificate is deliberately scoped to

- `-u'' = 1` on `[0,1]`,
- homogeneous Dirichlet endpoint data,
- a conforming arbitrary 1D partition,
- continuous piecewise-linear (`P1`) Galerkin FEM,
- unit diffusion.

For this class the exact solution is `u(x)=x(1-x)/2`, the Galerkin nodal values coincide with the exact nodal values, and on each element `K` of length `h_K`

`∫_K |u' - u_h'|² dx = h_K³ / 12`.

Therefore

`||u-u_h||_E² = Σ_K h_K³/12`.

v0.5 evaluates this identity using outward-rounded interval arithmetic over the stored binary64 mesh coordinates. This is a continuum discretization-error certificate for this theorem class, not a general-purpose FEM reliability theorem.

## Algebraic error
The computed floating-point solution may differ from the exact Galerkin discrete solution. That error remains separately certified by the v0.4 residual pipeline. v0.5 strengthens the SPD lower-bound mechanism with interval-verified `LDLᵀ` positivity of `A-αI` when Gershgorin is too weak.

The total energy error uses only the triangle inequality:

`||u-u_hat||_E <= ||u-u_h*||_E + ||u_h*-u_hat||_E`.

## Formal verification
v0.5 exports a Lean 4 theorem obligation, but the generated proof is intentionally incomplete. The corresponding formal verification record is `NOT_RUN` until Lean actually checks a completed artifact.

## Non-goals
v0.5 does not claim:

- a generic 2D/3D residual-estimator reliability theorem;
- interval-certified inverse Jacobians for arbitrary simplices;
- formal Lean proof completion;
- certified tetrahedral adaptivity;
- continuum certification for arbitrary diffusion tensors or forcing functions.
