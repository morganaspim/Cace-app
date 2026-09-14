# ADR 0017 — Sparse exact factorization and native assembly

## Decision

v0.16 adds two independent scalability paths.

1. A C++20 C-ABI kernel assembles the reduced one-dimensional P1 unit-diffusion stiffness matrix directly into CSR storage. Its output receives backend-equivalence evidence only after comparison with the canonical Python assembly on identical binary64 mesh nodes.
2. The verified sparse LDLᵀ path never materializes an `n × n` dense matrix. Stored binary64 CSR entries are interpreted as their exact rational values, sparse symbolic fill is discovered from the evolving factor graph, pivots are required to be exactly positive, and the factorization is reconstructed exactly on every factor-induced entry.

## Evidence boundary

Native C++ equivalence is numerical evidence. Exact sparse LDLᵀ is symbolic/exact evidence for the stored discrete matrix. Neither proves the continuum PDE.

## Why exact rational arithmetic?

A long SPD tridiagonal regression test showed dependency blow-up in direct outward-rounded interval LDLᵀ. Weakening the regression or accepting an uncertified floating factorization would violate CACE's refusal-first rules. Exact rational interpretation of IEEE-754 binary64 inputs avoids that ambiguity and gives exact reconstruction while remaining sparse.

## Limitations

The sparse verifier currently uses the natural ordering and therefore may experience fill on general two- and three-dimensional meshes. Fill-reducing orderings and a native sparse factorization are future work. Exact rational arithmetic can also become expensive for very large ill-conditioned systems.
