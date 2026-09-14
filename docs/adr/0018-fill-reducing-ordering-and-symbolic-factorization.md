# ADR 0018 — Fill-reducing ordering and symbolic factorization

## Status
Accepted for v0.17.

## Decision
CACE v0.17 introduces a deterministic exact-current-degree minimum-degree heuristic for symmetric sparse systems. It is not called AMD because no quotient-graph/approximate-degree machinery is implemented. A symbolic elimination pass predicts fill and factor structure before exact numeric verification.

The stored binary64 CSR entries are interpreted as exact rational numbers for the authoritative sparse LDLᵀ certificate. The matrix is symmetrically permuted, the symbolic factor pattern is generated without dense materialization, and exact rational LDLᵀ must reconstruct the permuted matrix exactly with strictly positive pivots.

## Evidence scopes
- Ordering/fill statistics: symbolic/combinatorial evidence.
- Exact sparse LDLᵀ reconstruction and positive pivots: symbolic/exact evidence about the stored discrete matrix.
- No continuum PDE claim follows from ordering or factorization.

## Reproducibility
Ties in the minimum-degree heuristic are broken by ascending original vertex index. Thus ordering and fill predictions are deterministic for a fixed CSR graph.

## Limitations
The heuristic is not AMD or nested dissection. It may reduce total fill while increasing maximum frontal size. v0.17 therefore reports both quantities separately and does not require both to improve.
