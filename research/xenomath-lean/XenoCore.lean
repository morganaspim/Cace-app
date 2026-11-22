import Mathlib

/- Xenomath research only. Carrier types encode the declared state domains.
   These statements do not assert novelty or correctness of a Python runtime. -/
namespace MerlinXeno

/-- One state must witness every selected predicate at the same threshold. -/
def JointWitness {X I : Type} (mu : I → X → Real)
    (selected : I → Prop) (threshold : Real) : Prop :=
  ∃ x, ∀ i, selected i → threshold ≤ mu i x

/-- The closed-threshold Dowker relation, with the same witnesses. -/
def DowkerWitness {X I : Type} (cost : I → X → Real)
    (selected : I → Prop) (radius : Real) : Prop :=
  ∃ x, ∀ i, selected i → cost i x ≤ radius

theorem joint_downward {X I : Type} (mu : I → X → Real)
    (small large : I → Prop) (a : Real)
    (hsub : ∀ i, small i → large i) :
    JointWitness mu large a → JointWitness mu small a := by
  rintro ⟨x, hx⟩
  exact ⟨x, fun i hi => hx i (hsub i hi)⟩

theorem joint_threshold {X I : Type} (mu : I → X → Real)
    (selected : I → Prop) (a b : Real) (hab : a ≤ b) :
    JointWitness mu selected b → JointWitness mu selected a := by
  rintro ⟨x, hx⟩
  exact ⟨x, fun i hi => le_trans hab (hx i hi)⟩

theorem joint_dowker_equivalence {X I : Type} (mu : I → X → Real)
    (selected : I → Prop) (a : Real) :
    JointWitness mu selected a ↔
      DowkerWitness (fun i x => 1 - mu i x) selected (1 - a) := by
  constructor
  all_goals
    rintro ⟨x, hx⟩
    refine ⟨x, ?_⟩
    intro i hi
    have h := hx i hi
    linarith

theorem joint_pullback_surjective {X Y I : Type}
    (mu : I → Y → Real) (selected : I → Prop) (a : Real)
    (f : X → Y) (hf : Function.Surjective f) :
    JointWitness (fun i x => mu i (f x)) selected a ↔
      JointWitness mu selected a := by
  constructor
  · rintro ⟨x, hx⟩
    exact ⟨f x, hx⟩
  · rintro ⟨y, hy⟩
    obtain ⟨x, hxy⟩ := hf y
    refine ⟨x, ?_⟩
    intro i hi
    simpa [hxy] using hy i hi

/-- A cover or simulation relation supplies the explicit matching premise. -/
theorem joint_transfer {X Y I : Type} (mu : I → X → Real)
    (nu : I → Y → Real) (selected : I → Prop) (a e : Real)
    (hmatch : ∀ x, ∃ y, ∀ i, selected i → mu i x ≤ nu i y + e) :
    JointWitness mu selected a → JointWitness nu selected (a - e) := by
  rintro ⟨x, hx⟩
  obtain ⟨y, hy⟩ := hmatch x
  refine ⟨y, ?_⟩
  intro i hi
  have h1 := hx i hi
  have h2 := hy i hi
  linarith

theorem pointwise_error_composes {X Y Z I : Type}
    (mu : I → X → Real) (nu : I → Y → Real) (rho : I → Z → Real)
    (f : X → Y) (g : Y → Z) (e d : Real)
    (hf : ∀ i x, mu i x ≤ nu i (f x) + e)
    (hg : ∀ i y, nu i y ≤ rho i (g y) + d) :
    ∀ i x, mu i x ≤ rho i (g (f x)) + (e + d) := by
  intro i x
  have h1 := hf i x
  have h2 := hg i (f x)
  linarith

theorem joint_two_way_stability {X Y I : Type}
    (mu : I → X → Real) (nu : I → Y → Real)
    (selected : I → Prop) (a e : Real)
    (hforward : ∀ x, ∃ y, ∀ i, selected i → mu i x ≤ nu i y + e)
    (hbackward : ∀ y, ∃ x, ∀ i, selected i → nu i y ≤ mu i x + e) :
    (JointWitness mu selected a → JointWitness nu selected (a - e)) ∧
    (JointWitness nu selected a → JointWitness mu selected (a - e)) := by
  exact ⟨joint_transfer mu nu selected a e hforward,
    joint_transfer nu mu selected a e hbackward⟩

/-- A covering certificate can rule out a joint witness without claiming
    that a finite point cloud is the entire continuum. -/
theorem exclusion_from_cover {X I C : Type} (mu : I → X → Real)
    (selected : I → Prop) (cell : C → X → Prop) (a upper : Real)
    (hcover : ∀ x, ∃ c, cell c x)
    (hbound : ∀ c, ∃ i, selected i ∧
      ∀ x, cell c x → mu i x <= upper)
    (hgap : upper < a) :
    Not (JointWitness mu selected a) := by
  rintro ⟨x, hx⟩
  obtain ⟨c, hc⟩ := hcover x
  obtain ⟨i, hi, hb⟩ := hbound c
  have h1 := hx i hi
  have h2 := hb x hc
  linarith

theorem affine_error_transport (u v scale offset e : Real)
    (h : abs (u - v) ≤ e) :
    abs ((scale * u + offset) - (scale * v + offset)) ≤ abs scale * e := by
  calc
    abs ((scale * u + offset) - (scale * v + offset))
        = abs (scale * (u - v)) := by congr 1; ring
    _ = abs scale * abs (u - v) := abs_mul _ _
    _ ≤ abs scale * e := mul_le_mul_of_nonneg_left h (abs_nonneg scale)

theorem simplex_three_bound (a b c : Real) (hsum : a + b + c = 1) :
    min a (min b c) ≤ (1 : Real) / 3 := by
  have ha := min_le_left a (min b c)
  have hb := le_trans (min_le_right a (min b c)) (min_le_left b c)
  have hc := le_trans (min_le_right a (min b c)) (min_le_right b c)
  linarith

/-- The fractal application must separately prove its first-level corner premise. -/
theorem corner_three_bound (a b c : Real) (hsum : a + b + c = 1)
    (hcorner : (1 : Real) / 2 ≤ a ∨ (1 : Real) / 2 ≤ b ∨ (1 : Real) / 2 ≤ c) :
    min a (min b c) ≤ (1 : Real) / 4 := by
  have ha := min_le_left a (min b c)
  have hb := le_trans (min_le_right a (min b c)) (min_le_left b c)
  have hc := le_trans (min_le_right a (min b c)) (min_le_right b c)
  rcases hcorner with h | h | h <;> linarith

theorem corner_bound_attained :
    min ((1 : Real) / 2) (min ((1 : Real) / 4) ((1 : Real) / 4)) = (1 : Real) / 4 := by
  norm_num

theorem simplex_bound_attained :
    min ((1 : Real) / 3) (min ((1 : Real) / 3) ((1 : Real) / 3)) = (1 : Real) / 3 := by
  norm_num

theorem pairwise_equation_witnesses :
    (∃ x y : Real, x = 0 ∧ y = 0) ∧
    (∃ x y : Real, x = 0 ∧ x + y = 1) ∧
    (∃ x y : Real, y = 0 ∧ x + y = 1) := by
  refine ⟨⟨0, 0, ?_, ?_⟩, ⟨0, 1, ?_, ?_⟩, ⟨1, 0, ?_, ?_⟩⟩ <;> norm_num

theorem no_joint_equation_witness :
    Not (∃ x y : Real, x = 0 ∧ y = 0 ∧ x + y = 1) := by
  rintro ⟨x, y, hx, hy, hsum⟩
  linarith

/-- Exact nonlinear shear for the nonresonant worked example. -/
theorem normal_form_inverse (x y : Real) :
    (y - x ^ 2 / 3) + x ^ 2 / 3 = y := by ring

theorem normal_form_pushforward (x y : Real) :
    (-y + x ^ 2) - (2 * x / 3) * x = -(y - x ^ 2 / 3) := by ring

theorem spectral_packet_closure (x z : Real) :
    (4*x^3 + 6*x*z)*x + (3*x^2 + 2*z)*(2*z) =
      4*(x^4 + 3*x^2*z + z^2) := by ring

end MerlinXeno
#print axioms MerlinXeno.joint_downward
#print axioms MerlinXeno.joint_threshold
#print axioms MerlinXeno.joint_dowker_equivalence
#print axioms MerlinXeno.joint_pullback_surjective
#print axioms MerlinXeno.joint_transfer
#print axioms MerlinXeno.pointwise_error_composes
#print axioms MerlinXeno.joint_two_way_stability
#print axioms MerlinXeno.exclusion_from_cover
#print axioms MerlinXeno.affine_error_transport
#print axioms MerlinXeno.simplex_three_bound
#print axioms MerlinXeno.corner_three_bound
#print axioms MerlinXeno.corner_bound_attained
#print axioms MerlinXeno.simplex_bound_attained
#print axioms MerlinXeno.pairwise_equation_witnesses
#print axioms MerlinXeno.no_joint_equation_witness
#print axioms MerlinXeno.normal_form_inverse
#print axioms MerlinXeno.normal_form_pushforward
#print axioms MerlinXeno.spectral_packet_closure
