# Post-v3.25 continuum H¹/H(div) closure roadmap

The finite exact certificate track and the continuum functional-analytic track are intentionally separated.  v3.22-v3.25 must not be cited as a proof of the continuum trace theorem.

## v3.26 — Sobolev-space interfaces

Formalize the domain assumptions and the exact spaces required by the continuum theorem: `H¹`, `H¹₀` where appropriate, `H(div)`, weak gradients, weak divergence, and the coefficient-weighted energy pairing used by CACE.  State the minimum domain regularity explicitly rather than hiding it in helper lemmas.

Exit criterion: the continuum target theorem type-checks with every analytic assumption visible, but may still depend on named trace/density lemmas.

## v3.27 — H(div) normal trace

Formalize or connect to Mathlib results for the normal trace of `H(div)` fields on the chosen class of domains.  Prove the boundedness/duality statement actually needed by the CACE Green identity.  Keep this separate from finite-element normal-flux cancellation.

Exit criterion: a theorem exposes the normal trace in the correct boundary dual space with no `sorry`, `admit`, or hidden finite-dimensional surrogate.

## v3.28 — Density and approximation bridge

Prove the density/approximation statements needed to pass from smooth fields to `H¹ × H(div)` data.  Track convergence of the gradient, divergence, and boundary duality terms explicitly.

Exit criterion: the smooth Green identity can be transported to the target Sobolev spaces under stated assumptions.

## v3.29 — Continuum Green identity

Prove the weak Green identity used by the CACE orthogonality argument:

`⟨q, ∇v⟩ + ⟨div q, v⟩ = ⟨γₙ q, γ v⟩_boundary`

with the precise sign convention and duality spaces fixed in the theorem statement.

Exit criterion: the identity is machine-formal for the declared domain class and spaces, independently of any discrete mesh certificate.

## v3.30 — Continuum Prager–Synge closure

Connect admissible primal and flux spaces, equilibrium, boundary conditions, weighted energy, and the continuum Green identity to derive the continuum orthogonality and Prager–Synge/hypercircle endpoint.

Exit criterion: the continuum theorem depends only on explicitly formalized analytic assumptions and previously closed lemmas.  The finite `MeshCertificate` track may provide certified approximations/examples, but is not used as a substitute for the continuum proof.

## Required discipline for every release

1. No finite-dimensional exact certificate is labeled a continuum theorem.
2. No numerical experiment is promoted to formal evidence.
3. Every generated Lean artifact is `FORMAL` only after the pinned external CI build passes.
4. Domain regularity, trace spaces, coefficient assumptions, and sign conventions remain explicit.
5. Negative tests should include violated boundary conditions, non-equilibrated fluxes, and incompatible trace assumptions where constructible.
