# CACE Studio VRE v1.01 — Reliability Closure

## Main result
The standard residual reliability theorem for conforming P1 Poisson FEM on uniformly
shape-regular affine simplicial mesh families is now represented as a **reviewed imported
theorem contract** with an executable hypothesis matcher.

The release imports as reviewed mathematics:
- Scott-Zhang local L2 approximation,
- Scott-Zhang local H1 stability,
- scaled trace inequality on shape-regular simplices,
- mesh-uniform finite patch overlap.

CACE then derives the face estimate and the mesh-size-independent constant structure

    C_rel = sqrt(C_0^2 N_K + C_E^2 N_E) / sqrt(alpha).

## Evidence boundary
- reviewed theorem closure: YES
- machine-formal closure: NO
- executable hypothesis refusal: YES

No imported analytic theorem is relabeled as machine-checked.
