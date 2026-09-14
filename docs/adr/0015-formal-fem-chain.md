# ADR 0015 — Formal FEM chain in v0.14

## Decision

CACE v0.14 extends the independent exact-arithmetic formal checker from reference barycentric identities to a tightly scoped FEM theorem chain.

The checker re-derives, using exact rational arithmetic:

1. invertibility of supplied rational simplex affine maps in dimensions 1–3;
2. the physical P1 gradient transformation `grad_x phi = B^{-T} grad_hat phi`;
3. local unit-diffusion stiffness symmetry and positive semidefiniteness through the exact Gram representation;
4. the 1D homogeneous-Dirichlet P1 stiffness edge-difference energy identity and positive definiteness for the supplied mesh;
5. for `u(x)=x(1-x)/2`, the exact local interpolation-energy identity `int_K |u'-(I_h u)'|^2 = h_K^3/12`, and its exact global sum on the supplied rational mesh.

## Trust boundary

The theorem-registry promotion boundary re-runs the checker and does not trust upstream `machine_checked` flags. The exact checker is a small project-specific proof kernel, not Lean. Its results are formal relative to that kernel and Python exact integer/Fraction semantics.

## Non-claims

v0.14 does not formally prove the general 2D residual-estimator reliability theorem, arbitrary-mesh convergence, interval arithmetic correctness, or the full FEM implementation. Those remain separate obligations.
