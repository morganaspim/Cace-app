# ADR 0016 — Formal assembly invariants + verified factorization

CACE v0.15 separates two evidence layers.

1. The exact rational formal kernel machine-checks a supplied 1D P1 assembly instance: local row sums vanish, the assembled full matrix is symmetric, the constant vector is in its nullspace before boundary conditions, and homogeneous endpoint Dirichlet elimination gives an SPD reduced matrix through exact LDL^T pivots.
2. The certified-linear-algebra layer verifies the stored binary64 reduced matrix with outward-rounded interval LDL^T and an independent interval reconstruction enclosure.

The first produces formal evidence scoped to the exact rational proof artifact. The second produces interval-certified evidence scoped to the stored discrete matrix. Neither implies a formal proof of the continuum PDE.

The reference interval factorization currently densifies CSR. A production sparse factorization is future work; this limitation is explicit and does not alter the certificate semantics.
