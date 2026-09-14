# ADR 0026 — v1.26–v1.30 Real Equilibrated-Flux Engine

The v1.26–v1.30 sequence implements a concrete lowest-order Raviart–Thomas (RT0)
flux pipeline on conforming affine triangular meshes.

## Convention

For `-div(A grad u)=f`, CACE uses `sigma=-A grad u`, hence admissibility requires
`div sigma=f`.

## Stages

- v1.26: exact RT0 basis normalization and divergence audit on rational triangles.
- v1.27: global canonical edge DOFs with opposite local signs on interior edges,
  yielding H(div) normal continuity by construction.
- v1.28: exact constrained RT0 equilibration on a cell fixture.
- v1.29: exact global cell-equilibrium verification on a multi-cell mesh.
- v1.30: reviewed Prager–Synge theorem contract plus exact admissibility and exact
  rational constitutive-mismatch integration for a unit-square Poisson fixture.

## Evidence boundary

The RT0 algebra, topology, balance equations, and mismatch-square integration are
checked exactly for rational fixtures. Prager–Synge itself is imported as a reviewed
mathematical theorem and is not relabeled as machine-formal evidence.
