# ADR 0026 — v1.31–v1.50 estimator-quality development

The release sequence implements the previously declared roadmap:

- v1.31–v1.35: estimator quality, local efficiency machinery, improved RT0 reconstruction,
  piecewise SPD coefficients, projected affine sources, and oscillation accounting.
- v1.36–v1.40: guaranteed-bound stopping/marking policy and adaptive convergence/complexity audits.
- v1.41–v1.45: P2 triangular basis, cubic quadrature, polynomial reproduction, exact local
  P2 stiffness audit, and explicit refusal to claim RT1 before its DOFs are implemented.
- v1.46–v1.50: bounded goal-functional catalog, exact finite-dimensional DWR identity,
  localized dual-weighted contributions, goal marking, and milestone integration.

Reviewed mathematical theorems are never silently promoted to machine-formal status.
