# ADR 0005 — Dimension-generic simplex FEM core

Date: 2026-09-13
Status: Accepted for v0.3

## Decision
Represent a d-dimensional P1 finite element mesh as vertices in R^d and d-simplices with d+1 vertex indices. Derive boundary facets by codimension-one incidence counting. Use one affine-coordinate/Jacobian implementation for segments, triangles, and tetrahedra.

## Rationale
This removes duplicated 1D/2D/3D basis logic and makes local identities independently testable. It also creates a stable data contract for future C++/GPU sparse kernels.

## Evidence boundary
The implementation checks nondegeneracy, facet incidence, barycentric identities, quadrature moments, matrix symmetry/SPD, and algebraic residuals. These checks do not prove general FEM convergence or a posteriori estimator reliability. v0.3 therefore labels the ND residual estimator as a diagnostic.

## Refinement boundary
Conforming refinement is implemented for 1D and 2D. Adaptive 2D uses Dörfler cell marking plus shared-edge red/green refinement. Tetrahedral adaptivity is rejected rather than approximated by a potentially nonconforming scheme.
