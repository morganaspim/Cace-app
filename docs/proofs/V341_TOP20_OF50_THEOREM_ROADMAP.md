# v3.41+ Theorem Roadmap — Top 20 Selected from 50 Candidates

Status: planning document only. No theorem in this document is claimed proved until it appears in Lean, is admitted to audited scope, passes the kernel/metadata/axiom pipeline, and receives canonical qualification under the normal CACE promotion rules.

Date: 2026-09-19

Qualified baseline used for this ranking:

- v3.40 attested source: `e0442f28fec309152fafd21d9f7c7d5c07cf401d`
- v3.40 canonical run: `35458894012`
- proof contract: `cace.proof.v330.continuum-proof-strengthening.v3`
- qualified contract: 48 endpoints / 18 audited Lean sources
- proof-contract SHA-256: `2c57ca63f25c044953613fb2256e002da7e75d9adb8343d048e26172411e623f`

The later provenance/sanity-only descendants do not change the mathematical baseline.

## Ranking method

Candidates were ranked by:

1. **Gap closure** — directly removes an explicit current nonclaim or caller-supplied hypothesis.
2. **Dependency leverage** — unlocks several downstream theorems rather than one wrapper.
3. **Proof tractability** — likely expressible with the already-qualified box/Green/closure infrastructure and existing Mathlib facts.
4. **Reusability** — useful for future mixed-boundary, weighted-energy, FEM, and runtime bridges.
5. **Rigor safety** — can be stated without pretending arbitrary H¹ fields have zero trace or importing unproved PDE assumptions.

Ties are broken by dependency order: a prerequisite ranks ahead of a theorem that consumes it.

## The explicit v3.40 gap

`ZeroBoundaryClosure.lean` proves:

- the functional zero-boundary submodule is closed;
- closure of any already-certified zero-boundary core remains zero-boundary;
- bounded-box equilibrated Prager–Synge can consume membership in such a closure.

It deliberately **does not construct a useful boundary-vanishing box core**.

That is the highest-value next gap.

# Selected Top 20

## 1. Concrete smooth face-vanishing scalar submodule

Proposed object:

`BoxBoundaryVanishingSmoothScalar a b`

Define the submodule of `BoxSmoothScalar n` whose scalar value is zero on every upper and lower face of the closed box.

Why #1: this creates the missing concrete object from which every later boundary theorem can flow.

Scope rule: only the explicitly defined face-vanishing functions belong; arbitrary Schwartz functions do not.

## 2. Upper/lower face membership characterization

Prove a clean iff theorem expanding membership in `BoxBoundaryVanishingSmoothScalar a b` into the pointwise upper/lower face conditions.

Why: downstream flux proofs should consume a stable theorem rather than unfold a custom submodule representation repeatedly.

## 3. Zero upper-face product integrand

For boundary-vanishing scalar `v` and any smooth vector field `q`, prove

`scalarTimesVector v q`

has zero normal-coordinate integrand on each upper box face.

Why: first concrete bridge from the scalar boundary condition to classical flux cancellation.

## 4. Zero lower-face product integrand

Lower-face analogue of #3.

Why: needed independently because signed box flux is upper minus lower.

## 5. Upper-face flux vanishes

Use #3 to prove each `upperFaceFlux` of the product field is zero.

Why: converts pointwise face vanishing into the integral object used by the existing normal-trace theory.

## 6. Lower-face flux vanishes

Use #4 to prove each `lowerFaceFlux` of the product field is zero.

## 7. Smooth classical boundary pairing vanishes

Prove

`smoothNormalFluxPairing a b q v = 0`

for boundary-vanishing smooth scalar `v` and arbitrary smooth vector `q`.

Why: aggregates the face results into the exact classical boundary term used by Green's theorem.

## 8. Smooth classical normal trace of the product vanishes

Equivalent/bridge form:

`smoothBoxNormalTrace a b (scalarTimesVector v q) = 0`.

Why: connects directly to `boxGraphNormalTrace_smooth_eq_classical_auto`.

## 9. Fixed-test-field normal-trace continuous functional

Add a reusable generic helper that, for fixed `v : V`, packages

`q ↦ G.normalTrace q v`

as a continuous linear functional on `Q`.

Why: the classical theorem only starts with smooth `q`; `HasZeroBoundaryTrace` quantifies over every closed-graph `q`. Density/continuity must be explicit rather than hand-waved.

## 10. Dense-flux-core annihilation implies functional zero boundary trace

Generic theorem:

if a fixed `v` is annihilated by the normal-trace pairing for every `q` in a dense submodule of `Q`, then

`HasZeroBoundaryTrace G v`.

Why: this is the rigorous closure step needed to turn smooth classical face cancellation into the all-`q` functional trace predicate.

## 11. Embedded smooth face-vanishing scalar has functional zero trace

For `v : BoxBoundaryVanishingSmoothScalar a b`, prove its existing embedded H¹ graph point satisfies

`HasZeroBoundaryTrace (boxGraphBoundedGreenPairing a b) ...`.

Proof route:

smooth classical trace agreement + #8 + density of `BoxHDivDenseSmoothCore` + #10.

Why: this is the first concrete theorem that discharges the abstract zero-boundary hypothesis used by the continuum chain.

## 12. Linear map from smooth scalar fields into the closed box H¹ graph space

Package the existing `smoothBoxH1ClosedPoint` construction as a genuine linear map.

Proposed object:

`smoothBoxH1ClosedMap a b`.

Why: lets CACE form image submodules cleanly instead of encoding existential carrier predicates by hand.

## 13. Concrete boundary-vanishing smooth graph core

Define

`BoxH1ZeroBoundarySmoothGraphCore a b`

as the image of `BoxBoundaryVanishingSmoothScalar a b` under #12.

Why: this is the concrete `V0` that v3.40 intentionally left abstract.

## 14. Concrete core is contained in the functional zero-boundary submodule

Prove:

`BoxH1ZeroBoundarySmoothGraphCore a b ≤ zeroBoundarySubmodule (boxGraphBoundedGreenPairing a b)`.

Why: packages #11 as the exact submodule inclusion consumed by `ZeroBoundaryClosure.lean`.

## 15. Define the concrete box H¹-zero graph space

Define:

`BoxH10GraphSpace a b := (BoxH1ZeroBoundarySmoothGraphCore a b).topologicalClosure`.

This is a graph-closure definition, not a claim that it equals every classical presentation of `H₀¹`.

Why: gives the project a domain-honest zero-boundary graph space without overclaiming a Sobolev trace equivalence not yet proved.

## 16. Every concrete H¹-zero graph datum has functional zero trace

Prove:

`BoxH10GraphSpace a b ≤ zeroBoundarySubmodule (boxGraphBoundedGreenPairing a b)`

and a pointwise `HasZeroBoundaryTrace` form.

Proof route: #14 + already-qualified v3.40 `topologicalClosure_le_zeroBoundarySubmodule`.

Why: closes the exact explicit v3.40 nonclaim at the level CACE can presently justify.

## 17. Pairwise trace cancellation implies pairwise volume cancellation

Generic theorem with weaker assumptions than `HasZeroBoundaryTrace`:

if

`G.normalTrace q v = 0`

for one specified pair `(q,v)`, then by weak Green

`G.volumePairing q v = 0`.

Why: Prager–Synge only needs cancellation of its actual cross-term pair. The stronger all-`q` boundary predicate should remain available, but callers need not prove more than the theorem consumes.

## 18. Pairwise trace cancellation implies orthogonality

Generic theorem:

single-pair trace cancellation + cross-term identification implies

`inner eGrad eFlux = 0`.

Why: reusable weak-Green orthogonality endpoint with minimal relevant boundary hypothesis.

## 19. Pairwise-trace continuum Prager–Synge

Generic Prager–Synge theorem whose boundary premise is only

`G.normalTrace q v = 0`

for the particular `q,v`.

Why: strictly broadens useful theorem application without weakening any proof; it states exactly the hypothesis actually needed by the cross-term.

## 20. Fully concrete box H¹-zero equilibrated Prager–Synge endpoint

Combine #15/#16 with the already-qualified divergence-zero bridge to prove a bounded-box endpoint taking:

- `q : BoxHDivGraphClosedSpace a b`;
- `v : BoxH10GraphSpace a b`;
- `q.1.2 = 0`;

and no caller-supplied arbitrary core or pointwise zero-boundary proof.

Why: this is the most valuable user-facing theorem produced by the batch. It removes both abstract `V0/hV0` arguments from the v3.40 endpoint while preserving the divergence-zero hypothesis honestly.

# Remaining Candidates 21–50

These remain useful, but rank below the selected 20 because they are either downstream, require more Mathlib analysis, or solve less immediate gaps.

## 21. Weighted-energy H¹-zero box hypercircle

Specialize `boxGraphWeightedHypercircle` to the concrete `BoxH10GraphSpace`.

## 22. Membership-form H¹-zero Prager–Synge wrapper

A convenient theorem accepting ordinary closed-box H¹ graph data plus membership in `BoxH10GraphSpace`.

## 23. Specialized closedness of the concrete H¹-zero graph space

Expose `IsClosed (BoxH10GraphSpace a b : Set ...)`.

## 24. Specialized trace-norm bound on the box graph pairing

Instantiate the generic `BoundedGreenPairing.normalTrace_bound` with the concrete box spaces.

## 25. Define smooth zero-normal H(div) face condition

Vector analogue: normal component vanishes on every box face.

## 26. Define smooth zero-normal H(div) submodule

Linear structure for #25.

## 27. Smooth zero-normal vector implies zero boundary pairing against arbitrary smooth scalar

Classical q-side boundary cancellation.

## 28. Dense scalar-core extension of zero-normal trace to all H¹ graph tests

q-side analogue of selected #9/#10.

## 29. Define closed zero-normal H(div) graph core/space

Closure of the explicit smooth zero-normal vector core.

## 30. Prager–Synge using zero-normal flux and arbitrary primal test field

Alternative boundary mechanism: make the flux error carry the zero-boundary condition instead of the primal error.

## 31. Face-mask type for mixed boundary conditions

Represent a finite partition of box faces into Dirichlet/Neumann portions.

## 32. Dirichlet face-vanishing scalar submodule for a face mask

Only selected faces require scalar vanishing.

## 33. Neumann zero-normal vector submodule for complementary faces

Only the complementary selected faces require zero normal flux.

## 34. Complementary mixed face conditions imply zero classical boundary pairing

Combine #32/#33 face by face.

## 35. Mixed-boundary functional trace cancellation

Extend #34 from smooth cores to closed graph data.

## 36. Mixed-boundary Prager–Synge

Concrete hypercircle theorem with complementary boundary conditions.

## 37. Weighted mixed-boundary hypercircle

SPD-energy analogue of #36.

## 38. Define a polynomial box boundary bubble

A product such as coordinate lower/upper boundary factors that vanishes on every face.

This is a constructive generator for nontrivial boundary-vanishing functions.

## 39. Prove the box bubble vanishes on every face

Exact finite-product algebraic identity.

## 40. Prove multiplication by the box bubble preserves Schwartz class

Mathlib-analysis/API work; useful but more involved than the direct predicate core.

## 41. Bubble-weighted Schwartz fields lie in the face-vanishing scalar submodule

Constructive family of members for the selected #1 object.

## 42. Define bubble-generated H¹-zero smooth graph core

Image/range of the bubble multiplication operator.

## 43. Bubble-generated core lies in the concrete H¹-zero graph space

Connect constructive generators to #15.

## 44. Define interior-compact-support smooth scalar core

Use smooth/Schwartz fields whose support stays inside the box interior.

## 45. Interior compact support implies face vanishing

Geometric support theorem.

## 46. Compact-support graph closure lies in the concrete H¹-zero graph space

Safe one-way inclusion.

## 47. Equality of compact-support closure and concrete H¹-zero space under an explicit approximation criterion

Conditional theorem only; no unconditional density claim until an actual approximation theorem is supplied.

## 48. Boundary-preserving regularizer criterion for equality with the full functional zero-boundary submodule

A generic theorem specifying exactly what a regularizer must prove before CACE may identify the explicit core closure with all functional zero-trace graph data.

## 49. Unconditional real whole-space H(div) graph-density bridge

Use the already-qualified complex Hilbert whole-space H(div) density theorem to investigate whether the operational real graph closure can be identified unconditionally with `RealHDivDistributionalPreimage`, eliminating the old regularizer-only route if scalar-complexification arguments suffice.

Risk: requires careful real/complex image/surjectivity reasoning; do not claim it until proved.

## 50. Bounded-domain H(div) density / normal-trace core theorem

Construct a real bounded-box H(div) core with the correct boundary behavior and prove a useful density/closure statement.

Why last: extremely valuable long term, but analytically harder than closing the current H¹-zero core gap and therefore a poor first target for the immediate batch.

# Recommended batch partition

The selected 20 should **not** be pushed blindly as one giant untested formal commit.

Use the existing quarantine-first architecture.

### v3.41A — Classical boundary core foundation

Target selected ideas 1–8.

Expected result: a concrete smooth face-vanishing scalar core and machine-checked zero classical flux.

### v3.41B — Functional trace extension

Target 9–14.

Expected result: smooth face-vanishing graph points and the resulting smooth graph submodule are certified inside the functional zero-boundary submodule.

### v3.41C — Closed H¹-zero graph space

Target 15–16.

Expected result: concrete `BoxH10GraphSpace` with graph-norm closure inheritance and no claim of an unproved classical trace-space equivalence.

### v3.41D — Minimal-hypothesis orthogonality

Target 17–19.

Expected result: pairwise weak-Green/Prager–Synge endpoints that require only the boundary cancellation actually consumed.

### v3.41E — Concrete bounded-box endpoint

Target 20.

Expected result: equilibrated bounded-box Prager–Synge using the concrete H¹-zero graph space, with no arbitrary caller-supplied zero-boundary core.

# Qualification strategy

For each coherent new module or batch:

1. add it to quarantine;
2. run cheap/local/static checks first;
3. run one standalone Exact-Pin target with `compile_root=false`;
4. fix all discovered errors before promotion;
5. atomically promote imports + axiom audit + theorem metadata + proof contract + tests;
6. run one audited-root Exact-Pin with `compile_root=true`;
7. run one canonical exact-current-head qualification;
8. promote provenance in a separate qualification-insensitive overlay.

Do not add all 20 endpoints to the proof contract until their modules have passed standalone qualification.

# Nonclaims to preserve

Even after the selected 20 succeed, CACE should still **not** claim without further theorems that:

- every box H¹ graph datum has zero boundary trace;
- the new graph-closure definition equals every textbook/classical presentation of `H₀¹`;
- compactly supported smooth functions are dense in every desired bounded-domain Sobolev graph space unless that density is separately proved;
- arbitrary runtime finite-element fields satisfy the continuum hypotheses;
- bounded-domain H(div) density has been proved;
- mixed-boundary conditions are handled unless the later face-mask branch is actually implemented and qualified.

# Minimized user-dispatch execution mode

For this top-20 program, prefer a grouped interaction model:

1. Develop later sub-batches in quarantine while automatic cheap gates run.
2. Accumulate all ready quarantined modules.
3. Use **one** `CACE Batched Exact-Pin Lean Preflight` manual run to compile the ready module set and collect the complete failure frontier.
4. Fix all failures before requesting another batch run.
5. Promote the passing theorem set atomically into root/audit/metadata/contract scope.
6. Use the final canonical exact-head qualification as the expensive promotion gate rather than asking the user to dispatch one manual Lean job after every small theorem group.

The batch workflow is preflight only. It does not weaken the exact-head, kernel-axiom, theorem-metadata, proof-contract, or provenance requirements.

v3.41A ranks 1–8 already received their standalone exact-pin pass before this batching mode was introduced, so they do not need another standalone run.

