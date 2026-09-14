# ADR 0020 — Native multifrontal factorization and parallel subtrees

## Decision
v0.19 adds a native C++20 **scalar multifrontal LDLᵀ** algorithm. Each elimination-tree node owns a frontal matrix containing one pivot plus its higher-numbered update variables. Child Schur-complement contribution blocks are assembled into the parent front, the pivot is eliminated, and the remaining dense update block is passed upward.

Independent child subtrees may be evaluated with `std::async` up to a configured depth. Parallel execution is benchmark evidence only; it is not assumed faster on small systems.

The exact-rational sparse LDLᵀ verifier from v0.16–v0.18 remains the authoritative structural oracle. Native multifrontal results receive backend/numerical evidence only when factor nonzero counts, fill counts, solution accuracy, and residual checks agree with the oracle/reference problem.

## Supernodes
v0.19 retains symbolic supernode detection and reports supernode statistics. The numerical kernel is **not** called supernodal: it uses scalar pivots/fronts. A dense-block supernodal numeric kernel remains future work.

## Performance reporting
Wall times are median observed timings and are machine dependent. Memory figures are structural proxies (factor entries and dense frontal working-set entries), not operating-system peak RSS. Performance observations are never proof evidence.
