import Mathlib

namespace CACEFormal

/-!
# Paired-state continuum simplex core (experimental, quarantined)

A first formal kernel for the Merlin paired-continuum triangle. Each oriented
edge carries a continuous field into R × R. The two channels are independent
real coordinates; no complex-number semantics are assumed.

The triangle's endpoint gluing is explicit. A single state map applied
pointwise to all three edges preserves gluing. This is a structural theorem,
not an interior-extension theorem and not a claim about arbitrary nonlinear
boundary data.
-/

/-- Two simultaneous real-valued channels at one point of an edge. -/
abbrev PairState := ℝ × ℝ

/-- A parameterized edge carrying two simultaneous real values. -/
abbrev PairEdgeField := ℝ → PairState

/-- The three oriented edges of a triangle, each carrying a continuum field. -/
structure PairedContinuumTriangle where
  ab : PairEdgeField
  bc : PairEdgeField
  ca : PairEdgeField

namespace PairedContinuumTriangle

/-- Endpoint compatibility at the three shared vertices. -/
def EndpointGluing (T : PairedContinuumTriangle) : Prop :=
  T.ab 1 = T.bc 0 ∧ T.bc 1 = T.ca 0 ∧ T.ca 1 = T.ab 0

/-- Pointwise application of one state transformation to every edge. -/
def map (F : PairState → PairState) (T : PairedContinuumTriangle) :
    PairedContinuumTriangle where
  ab := fun t => F (T.ab t)
  bc := fun t => F (T.bc t)
  ca := fun t => F (T.ca t)

/-- Shared-vertex gluing is invariant under a common state transformation. -/
theorem map_preserves_endpoint_gluing
    (F : PairState → PairState) (T : PairedContinuumTriangle)
    (h : EndpointGluing T) :
    EndpointGluing (map F T) := by
  rcases h with ⟨hab, hbc, hca⟩
  exact ⟨congrArg F hab, congrArg F hbc, congrArg F hca⟩

/-- Apply a potentially different state transformation to each oriented edge. -/
def mapEdges
    (F_AB F_BC F_CA : PairState → PairState)
    (T : PairedContinuumTriangle) : PairedContinuumTriangle where
  ab := fun t => F_AB (T.ab t)
  bc := fun t => F_BC (T.bc t)
  ca := fun t => F_CA (T.ca t)

/-- Edge-specific transformations preserve gluing exactly when their values
agree at each shared endpoint. The hypotheses are explicit rather than
silently assuming the three transformations are identical. -/
theorem mapEdges_preserves_endpoint_gluing
    (F_AB F_BC F_CA : PairState → PairState)
    (T : PairedContinuumTriangle)
    (hB : F_AB (T.ab 1) = F_BC (T.bc 0))
    (hC : F_BC (T.bc 1) = F_CA (T.ca 0))
    (hA : F_CA (T.ca 1) = F_AB (T.ab 0)) :
    EndpointGluing (mapEdges F_AB F_BC F_CA T) := by
  exact ⟨hB, hC, hA⟩

/-- Continuous edge fields remain continuous after a continuous state map. -/
theorem map_preserves_continuity
    (F : PairState → PairState) (hF : Continuous F)
    (T : PairedContinuumTriangle)
    (hab : Continuous T.ab) (hbc : Continuous T.bc) (hca : Continuous T.ca) :
    Continuous (map F T).ab ∧
    Continuous (map F T).bc ∧
    Continuous (map F T).ca := by
  exact ⟨hF.comp hab, hF.comp hbc, hF.comp hca⟩

/-- Edge-local continuous transformations preserve continuity on their
respective edge fields. Together with the endpoint theorem above, this gives
the exact local conditions for a continuous glued boundary field. -/
theorem mapEdges_preserves_continuity
    (F_AB F_BC F_CA : PairState → PairState)
    (hAB : Continuous F_AB) (hBC : Continuous F_BC) (hCA : Continuous F_CA)
    (T : PairedContinuumTriangle)
    (hab : Continuous T.ab) (hbc : Continuous T.bc) (hca : Continuous T.ca) :
    Continuous (mapEdges F_AB F_BC F_CA T).ab ∧
    Continuous (mapEdges F_AB F_BC F_CA T).bc ∧
    Continuous (mapEdges F_AB F_BC F_CA T).ca := by
  exact ⟨hAB.comp hab, hBC.comp hbc, hCA.comp hca⟩

end PairedContinuumTriangle

/-- A typed state transformation on the paired real state space. -/
abbrev PairStateMap := PairState → PairState

namespace PairStateMap

/-- Identity state transformation. -/
def id : PairStateMap := fun p => p

/-- Composition: inner is applied first, then outer. -/
def comp (outer inner : PairStateMap) : PairStateMap :=
  fun p => outer (inner p)

@[simp] theorem id_apply (p : PairState) : id p = p := rfl

@[simp] theorem comp_apply (outer inner : PairStateMap) (p : PairState) :
    comp outer inner p = outer (inner p) := rfl

/-- State-map composition is associative. -/
theorem comp_assoc (f g h : PairStateMap) :
    comp f (comp g h) = comp (comp f g) h := by
  funext p
  rfl

/-- Identity is a left identity for state-map composition. -/
theorem id_comp (f : PairStateMap) : comp id f = f := by
  funext p
  rfl

/-- Identity is a right identity for state-map composition. -/
theorem comp_id (f : PairStateMap) : comp f id = f := by
  funext p
  rfl

/-- The oriented triangle loop map: AB, then BC, then CA. -/
def triangleLoop (pAB pBC pCA : PairStateMap) : PairStateMap :=
  comp pCA (comp pBC pAB)

/-- The loop's action is explicitly ordered from AB to BC to CA. -/
theorem triangleLoop_apply
    (pAB pBC pCA : PairStateMap) (p : PairState) :
    triangleLoop pAB pBC pCA p = pCA (pBC (pAB p)) := rfl

end PairStateMap

/-- A pair-valued edge can be split into its two real coordinate channels. -/
def firstChannel (f : PairEdgeField) : ℝ → ℝ := fun t => (f t).1

def secondChannel (f : PairEdgeField) : ℝ → ℝ := fun t => (f t).2

/-- Recombining the two projections recovers the original paired field. -/
theorem pair_channels_reconstruct (f : PairEdgeField) (t : ℝ) :
    (firstChannel f t, secondChannel f t) = f t := by
  cases h : f t
  rfl


/-! ## Oriented triangle boundary cancellation

The following small chain-level kernel isolates the algebraic identity
\(\partial_1 \circ \partial_2 = 0\) for an oriented 2-simplex.
The edge [a,b] has boundary b-a, and the oriented triangle [a,b,c]
has boundary [b,c] - [a,c] + [a,b]. This theorem is independent of
the continuity and state-field assumptions above.
-/

/-- Boundary of an oriented 1-simplex [a,b], represented as an integer
0-chain. -/
def orientedEdgeBoundary {V : Type*} [DecidableEq V] (a b : V) :
    V →₀ ℤ :=
  Finsupp.single b 1 - Finsupp.single a 1

/-- Apply the vertex boundary to the alternating oriented boundary of
the triangle [a,b,c]. -/
def orientedTriangleBoundarySquared {V : Type*} [DecidableEq V]
    (a b c : V) : V →₀ ℤ :=
  orientedEdgeBoundary b c -
    orientedEdgeBoundary a c +
    orientedEdgeBoundary a b

/-- The boundary of the boundary of an oriented triangle is zero. -/
theorem oriented_triangle_boundary_squared_zero
    {V : Type*} [DecidableEq V] (a b c : V) :
    orientedTriangleBoundarySquared a b c = 0 := by
  ext v
  simp [orientedTriangleBoundarySquared, orientedEdgeBoundary]
  ring



/-! ## Oriented tetrahedron boundary cancellation

The oriented tetrahedron [a,b,c,d] has boundary
[b,c,d] - [a,c,d] + [a,b,d] - [a,b,c]. Each oriented face is
expanded into its three ordered edges. The resulting 1-chain is zero:
every edge occurs twice with opposite coefficients. This is a finite
chain identity and does not depend on the paired-continuum fields.
-/

/-- Boundary of an oriented 2-simplex [a,b,c], represented as an integer
1-chain on ordered vertex pairs. -/
def orientedFaceBoundary {V : Type*} [DecidableEq V] (a b c : V) :
    (V × V) →₀ ℤ :=
  Finsupp.single (b, c) 1 -
    Finsupp.single (a, c) 1 +
    Finsupp.single (a, b) 1

/-- Apply the edge boundary to the alternating oriented face boundary
of a tetrahedron [a,b,c,d]. -/
def orientedTetrahedronBoundarySquared {V : Type*} [DecidableEq V]
    (a b c d : V) : (V × V) →₀ ℤ :=
  orientedFaceBoundary b c d -
    orientedFaceBoundary a c d +
    orientedFaceBoundary a b d -
    orientedFaceBoundary a b c

/-- The boundary of the boundary of an oriented tetrahedron is zero.
The ordered-edge coefficients cancel in opposite-sign pairs. -/
theorem oriented_tetrahedron_boundary_squared_zero
    {V : Type*} [DecidableEq V] (a b c d : V) :
    orientedTetrahedronBoundarySquared a b c d = 0 := by
  ext edge
  simp [orientedTetrahedronBoundarySquared, orientedFaceBoundary]
  ring

end CACEFormal
