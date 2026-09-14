# ADR 0010 — Exact-solution-free bounds and tested visualization

v0.8 adds a deliberately conservative continuum energy-error bound that does not require a manufactured exact solution. On the reference triangle, horizontal slicing gives the Dirichlet Poincare bound `||v||_L2 <= (1/pi)||grad v||_L2`. Together with certified diffusion coercivity and an interval L2 norm for affine forcing, this bounds the continuum solution energy. The computed FEM energy is independently enclosed from the interval global stiffness matrix. Their sum bounds `||u-u_h||_A` by the triangle inequality.

This is not the sharper general residual-estimator reliability theorem and must not be labeled as such.

Visualization artifacts are non-proof evidence. The FEM visualization module renders actual mesh/solution data to PNG in headless mode. Tests verify that the file exists, is nontrivial, and has a valid PNG signature.
