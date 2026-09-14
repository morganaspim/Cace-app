# ADR 0022 — Reliability Theorem Discovery Engine (v0.76)

## Decision
CACE v0.76 introduces a theorem-discovery layer for the unresolved 2D conforming P1 residual reliability theorem.

The engine may:
- aggregate certified run observations,
- perform premise-ablation studies,
- locate and minimize *candidate* counterexamples,
- infer transparent empirical upper-envelope formulas for `E/eta`, and
- maintain an explicit analytic proof-obligation DAG.

It may **not** promote the mesh-uniform reliability theorem from numerical or synthetic evidence.

## Initial target
The narrow target is homogeneous-Dirichlet 2D conforming P1 Poisson on shape-regular triangular meshes with uniformly elliptic constant diffusion and residual/jump estimator.

## Current unresolved analytic obligations
1. residual representation from Galerkin orthogonality and elementwise Green identity,
2. local quasi-interpolation estimate,
3. local trace estimate,
4. finite-overlap bound,
5. composition with coercivity and implemented estimator definition.

## Evidence boundary
The built-in default corpus deliberately contains synthetic stress fixtures to test the discovery machinery. Those rows are labeled `synthetic-stress` and contribute **no continuum theorem evidence**.

A candidate constant is an empirical envelope over observed cases only. It is never a formal reliability constant until the analytic dependency graph is closed by proof evidence.
