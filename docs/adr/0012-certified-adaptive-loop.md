# ADR 0012 — Certified adaptive loop semantics (v0.11)

v0.11 composes the existing 2D P1 solve, interval discrete-solution enclosure, residual estimator, Dörfler marking, and conforming red/green refinement into one repeatable research loop.

Stopping semantics are evidence-sensitive:

* `discrete_enclosure_radius` is a certified statement about the exact solution of the stored discrete linear system.
* `estimator_upper` is a certified/recorded estimator-magnitude target, but is **not** called a continuum PDE error target.
* `continuum_error` is refused in v0.11 because the mesh-uniform residual-reliability theorem is not machine-dischargeable yet.

Every iteration is retained in the history, including mesh sizes, estimator values, marked cells, contraction factor, and enclosure radius. No prior iteration is overwritten.
