# ADR 0028 — v2.01–v2.25 production closure and ranked next steps

v2.01–v2.10 close the highest-priority production gaps carried forward from v2.0:
RT1 topology/orientation, mixed RT0 Poisson, Nedelec orientation, spectral certification
fixtures, and a continuum goal-error product bound.

Thirty candidate next steps were then ranked. The top fourteen were selected and mapped
one-to-one to v2.11–v2.24; the bottom sixteen were explicitly deferred. v2.25 is the
integration and qualification milestone.

The selected fourteen are:
1. Dual equilibrated goal bounds
2. Parabolic equilibrated-flux bounds
3. Space-time adaptive certification
4. hp adaptivity
5. 3D tetrahedral P1 continuum foundations
6. 3D RT0/H(div) equilibrated flux foundations
7. Nonlinear elliptic Newton-Kantorovich
8. Production Stokes mixed FEM foundations
9. Production Maxwell/Nedelec eigenproblem foundations
10. Certified domain decomposition
11. Certified multigrid
12. Anisotropic metric adaptation
13. Parametric uncertainty propagation
14. Certified reduced basis

Many of these releases establish exact fixtures, theorem contracts, or certification
plumbing rather than claiming full production solvers. Nonclaims are preserved in the
v2.25 milestone.
