import CACEFormal.SmoothBoxGreenAuto

/-!
# v3.30 kernel-assumption audit

This file is intentionally tiny. CI compiles it with the pinned Lean/mathlib toolchain and parses the
`#print axioms` output for the new analysis endpoints.  Promotion is rejected if a theorem depends on
`sorryAx` or on any axiom outside the small foundational whitelist enforced by the workflow.
-/

#print axioms CACEFormal.Continuum.smoothBoxProduct_hasFDerivAt
#print axioms CACEFormal.Continuum.smoothBoxProduct_divergence_eq_greenVolume
#print axioms CACEFormal.Continuum.smoothBoxGreen_schwartz
#print axioms CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto
