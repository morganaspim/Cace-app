# ADR 0026 — Evidence-aware automatic solver policy

v0.25 selects only among native CPU paths that pass the exact structural oracle and deterministic known-solution checks. Timing is local benchmark evidence. Conditional GPU dense-kernel equivalence does not imply that the full sparse solve may be routed to GPU.
