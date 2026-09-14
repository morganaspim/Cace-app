# ADR 0024 — v1.01 Reliability Closure

v1.01 changes the status of three former analytic obligations:

1. Scott-Zhang local L2/H1 approximation,
2. scaled simplex trace / derived face approximation,
3. mesh-family-uniform finite patch overlap.

These are encoded as **reviewed imported mathematical theorems** for conforming affine
uniformly shape-regular simplicial mesh families. They are not machine-formalized by CACE.

Under the admitted Poisson/P1 problem class, the residual reliability derivation is
closed at reviewed-theorem level:

    ||u-u_h||_A <= C_rel eta,

with C_rel independent of mesh size h and depending on dimension, shape regularity,
coercivity, and estimator/patch normalization.

Formal promotion remains prohibited until the imported analytic lemmas and the full weak
residual representation are machine checked.
