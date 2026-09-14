# ADR 0014 — Formal verification bridge

## Decision
CACE v0.13 introduces an independent exact-arithmetic proof kernel for a deliberately small theorem family before claiming any machine-checked PDE theorem.

The kernel checks canonical reference-simplex P1 barycentric identities using exact rational affine-polynomial normalization and exact vertex evaluation. The checker is invoked in a separate process and returns an attestation containing the checker version and SHA-256 hash of the proof artifact.

`EvidenceKind.FORMAL` is emitted only when that independent invocation exits successfully and the attestation matches the expected checker and claims.

## Scope
The machine-checked result proves only:

1. `sum_i lambda_i = 1` as an exact affine polynomial identity, and
2. `lambda_i(v_j) = delta_ij` on the canonical reference simplex,

for dimensions 1, 2, and 3 supported by the v0.13 kernel.

It does **not** prove FEM convergence, Poisson residual-estimator reliability, interval arithmetic correctness, or any continuum PDE theorem.

## Lean
Existing Lean PDE artifacts remain obligations. Lean is not available in the v0.13 build environment, so no Lean artifact is promoted to machine-checked status.
