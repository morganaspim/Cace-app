# ADR 0030 — v2.51–v3.0 production campaigns

Seven unresolved production capabilities were each researched with ten ranked approaches.
The top seven approaches in each target were mapped one-to-one to seven cumulative releases:

- v2.51–v2.57 global RT1 full sparse reconstruction
- v2.58–v2.64 arbitrary-mesh 3D equilibrated flux
- v2.65–v2.71 machine-formal Prager–Synge program
- v2.72–v2.78 Stokes mesh-family production
- v2.79–v2.85 Maxwell/Nedelec mesh-family production
- v2.86–v2.92 sparse verified eigensolver
- v2.93–v2.99 DG/SUPG/elasticity/contact/Helmholtz production paths
- v3.0 integrated qualification milestone

Lean is not installed in the execution environment. Therefore v2.70 exports a Lean theorem
skeleton and v2.71 attests the exact finite-dimensional hypercircle kernel, but the full
PDE-level Prager–Synge theorem remains NOT machine-formal. This is an explicit v3.0 nonclaim.
