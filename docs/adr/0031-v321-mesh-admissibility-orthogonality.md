# ADR 0031 - v3.21 Mesh Admissibility to Orthogonality

v3.21 closes the discrete finite-mesh bridge from certified mesh admissibility data
to primal/dual orthogonality in CACE's independent exact checker.

The bridge checks, rather than assumes:

- homogeneous boundary admissibility for the primal P1 trace;
- positive, consistently oriented conforming cells;
- divergence-free constant RT0-error fields in the supported fixture scope;
- interior normal-flux continuity/cancellation;
- the assembled global primal/dual pairing.

The generic Lean source theorem `mesh_admissibility_to_orthogonality` reduces the
global pairing to element divergence, physical-boundary, and interior-face terms,
then proves it vanishes when those certified hypotheses are zero.

External Lean evidence still requires a successful pinned Lean/mathlib v4.32.1
`lake build`. Uploaded Lean v4.0.0-m1 source/documentation material is useful for
bootstrap-layout reference but is not an executable or compatible replacement
toolchain.
