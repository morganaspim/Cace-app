# ADR-0006 — Certified FEM mathematics boundary

Date: 2026-09-13  
Status: Accepted for v0.4

## Decision

CACE v0.4 separates three claims that are often conflated:

1. **Assembly/problem-class validation** — checks that the supplied elementwise diffusion tensors are symmetric positive definite and that the reduced discrete matrix is SPD numerically.
2. **Discrete algebraic certification** — treats the stored binary64 CSR matrix, rhs, and computed solution as the exact *discrete* problem and uses outward-rounded interval arithmetic to enclose `A u - b`.
3. **Continuum FEM discretization certification** — requires an explicit reliability theorem artifact whose assumptions match the mesh, PDE coefficients, finite-element space, boundary conditions, estimator, and constants.

v0.4 implements (1) and (2). It deliberately ships no general theorem artifact for (3), so the continuum reliability gate returns `NOT_RUN` rather than upgrading an estimator to a certified PDE error bound.

## Algebraic theorem used

For a symmetric positive-definite matrix `A`, exact discrete solution `u*`, approximate solution `u`, and residual `r = A u - b`, if `alpha <= lambda_min(A)` and `alpha > 0`, then

`||u-u*||_2 <= ||r||_2 / alpha`

and

`||u-u*||_A <= ||r||_2 / sqrt(alpha)`.

v0.4 obtains `alpha` from an outward-rounded Gershgorin lower bound. This may fail to be positive even for an SPD matrix; in that case the certificate is unavailable by design.

## Floating-point scope

The interval residual certifies arithmetic over the **stored binary64 discrete data**. It does not yet interval-enclose the map from ideal real-valued mesh geometry and coefficients to the assembled FEM operator. That stronger verified-assembly problem is deferred.
