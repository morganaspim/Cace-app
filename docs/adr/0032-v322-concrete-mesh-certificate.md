# ADR 0032 - v3.22 Concrete Mesh Certificate

v3.22 promotes the supported square-with-center finite fixture from custom exact
checker evidence into a concrete Lean source certificate.

The new Lean module `CACEFormal.ConcreteMeshCertificate` represents:

- five rational vertices for the unit-square-plus-center mesh;
- four counter-clockwise triangular cells;
- four physical-boundary faces;
- four interior radial faces;
- a P1 scalar field by exact nodal values;
- constant-per-cell RT0-error flux data;
- exact cell pairings `0, -1/2, 0, 1/2`;
- zero divergence, zero boundary contribution, and interior normal-flux
  cancellation.

The concrete theorem `v322_discrete_prager_synge_from_concrete_mesh` feeds the
fixture into the v3.21 generic finite-sum bridge. Orthogonality is therefore
derived from the represented certificate data rather than accepted as an
unstructured theorem argument.

Nonclaims:

- v3.22 is not a general mesh generator theorem.
- Continuum H1/H(div) trace compatibility remains open.
- Arbitrary unstructured P1/RT0 meshes remain the next formal target.
