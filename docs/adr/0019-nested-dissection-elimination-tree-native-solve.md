# ADR 0019 — v0.18 ordering structure and native solve

CACE v0.18 benchmarks natural, deterministic current-degree minimum-degree, and geometric nested-dissection orderings for structured 2D P1 FEM systems. It derives the elimination tree and symbolic supernodes from the exact factor pattern. The chosen ordering is the one with minimum symbolic fill (then factor nnz, then name as deterministic tie-break).

The authoritative correctness oracle remains exact-rational sparse LDLᵀ of the stored binary64 CSR coefficients. The C++20 runtime performs a full permuted sparse left-looking LDLᵀ solve and must match the authoritative factor structure as well as a deterministic known solution/residual test. Native execution is numerical/backend evidence, not formal proof.

The current native algorithm is not called multifrontal or supernodal. v0.18 exports elimination-tree and supernode structure specifically to support a later implementation of those architectures.
