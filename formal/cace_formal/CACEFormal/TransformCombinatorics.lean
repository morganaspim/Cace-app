import CACEFormal.Hypercircle
import Mathlib.Data.List.Basic

namespace CACEFormal

/-!
# Certified low-cost geometry-transform combinatorics

This module is deliberately small and kernel-checkable.  It gives CACE a reusable
formal seam for composing geometry/data transforms while carrying two facts:

* a nonnegative discrete cost budget;
* exact preservation of the real inner product.

Inner-product preservation is strong enough to transport orthogonality and the
hypercircle identity.  The cost field is intentionally abstract: a caller may
instantiate it with operation count, cache misses, communication rounds, or any
other monotone integer budget.

The pair/triple/quadruple/quintuple/sextuple/septuple/octuple/nonuple
constructors are convenient named entry points for 2-through-9 module
combination search. The arbitrary `chain` constructor is the scalable 9+
endpoint.
-/

noncomputable section

/-- A transform with a discrete execution cost and a proof that it preserves
the real inner product exactly.  Linearity is not required at this interface;
specific transform families may add it in later modules. -/
structure CertifiedGeometryTransform
    (E : Type*) [SeminormedAddCommGroup E] [InnerProductSpace ℝ E] where
  toFun : E → E
  cost : Nat
  inner_preserving : ∀ x y, inner ℝ (toFun x) (toFun y) = inner ℝ x y

namespace CertifiedGeometryTransform

variable {E : Type*} [SeminormedAddCommGroup E] [InnerProductSpace ℝ E]

/-- Zero-cost identity transform. -/
def identity : CertifiedGeometryTransform E where
  toFun := fun x => x
  cost := 0
  inner_preserving := by
    intro x y
    rfl

/-- Composition preserves certification; costs add. -/
def comp (f g : CertifiedGeometryTransform E) : CertifiedGeometryTransform E where
  toFun := fun x => f.toFun (g.toFun x)
  cost := f.cost + g.cost
  inner_preserving := by
    intro x y
    rw [f.inner_preserving, g.inner_preserving]

@[simp] theorem identity_apply (x : E) :
    (identity : CertifiedGeometryTransform E).toFun x = x := rfl

@[simp] theorem identity_cost :
    (identity : CertifiedGeometryTransform E).cost = 0 := rfl

@[simp] theorem comp_apply (f g : CertifiedGeometryTransform E) (x : E) :
    (comp f g).toFun x = f.toFun (g.toFun x) := rfl

@[simp] theorem comp_cost (f g : CertifiedGeometryTransform E) :
    (comp f g).cost = f.cost + g.cost := rfl

/-- A certified transform carries orthogonality to transformed data. -/
theorem preserves_orthogonality
    (f : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    inner ℝ (f.toFun x) (f.toFun y) = 0 := by
  rw [f.inner_preserving, hxy]

/-- Consequently every certified transform transports the exact hypercircle
identity to the transformed error pair. -/
theorem hypercircle_after
    (f : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    ‖f.toFun x + f.toFun y‖ * ‖f.toFun x + f.toFun y‖ =
      ‖f.toFun x‖ * ‖f.toFun x‖ + ‖f.toFun y‖ * ‖f.toFun y‖ := by
  exact hypercircle_of_inner_eq_zero (f.preserves_orthogonality hxy)

/-- Named two-transform combination. -/
def pair (a b : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a b

/-- Named three-transform combination. -/
def triple (a b c : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b c)

/-- Named four-transform combination. -/
def quadruple (a b c d : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b (comp c d))

@[simp] theorem pair_cost (a b : CertifiedGeometryTransform E) :
    (pair a b).cost = a.cost + b.cost := rfl

@[simp] theorem triple_cost (a b c : CertifiedGeometryTransform E) :
    (triple a b c).cost = a.cost + (b.cost + c.cost) := rfl

@[simp] theorem quadruple_cost (a b c d : CertifiedGeometryTransform E) :
    (quadruple a b c d).cost = a.cost + (b.cost + (c.cost + d.cost)) := rfl

/-- Named five-transform combination. -/
def quintuple (a b c d e : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b (comp c (comp d e)))

/-- Named six-transform combination. -/
def sextuple (a b c d e f : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b (comp c (comp d (comp e f))))

/-- Named seven-transform combination. -/
def septuple (a b c d e f g : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b (comp c (comp d (comp e (comp f g)))))

/-- Named eight-transform combination. -/
def octuple (a b c d e f g h : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b (comp c (comp d (comp e (comp f (comp g h))))))

/-- Named nine-transform combination. -/
def nonuple (a b c d e f g h i : CertifiedGeometryTransform E) : CertifiedGeometryTransform E :=
  comp a (comp b (comp c (comp d (comp e (comp f (comp g (comp h i)))))))

@[simp] theorem quintuple_cost
    (a b c d e : CertifiedGeometryTransform E) :
    (quintuple a b c d e).cost =
      a.cost + (b.cost + (c.cost + (d.cost + e.cost))) := rfl

@[simp] theorem sextuple_cost
    (a b c d e f : CertifiedGeometryTransform E) :
    (sextuple a b c d e f).cost =
      a.cost + (b.cost + (c.cost + (d.cost + (e.cost + f.cost)))) := rfl

@[simp] theorem septuple_cost
    (a b c d e f g : CertifiedGeometryTransform E) :
    (septuple a b c d e f g).cost =
      a.cost + (b.cost + (c.cost + (d.cost + (e.cost + (f.cost + g.cost))))) := rfl

@[simp] theorem octuple_cost
    (a b c d e f g h : CertifiedGeometryTransform E) :
    (octuple a b c d e f g h).cost =
      a.cost + (b.cost + (c.cost + (d.cost + (e.cost + (f.cost + (g.cost + h.cost)))))) := rfl

@[simp] theorem nonuple_cost
    (a b c d e f g h i : CertifiedGeometryTransform E) :
    (nonuple a b c d e f g h i).cost =
      a.cost + (b.cost + (c.cost + (d.cost + (e.cost + (f.cost + (g.cost + (h.cost + i.cost))))))) := rfl

/-- Five certified geometry stages transport orthogonality. -/
theorem quintuple_preserves_orthogonality
    (a b c d e : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    inner ℝ ((quintuple a b c d e).toFun x)
      ((quintuple a b c d e).toFun y) = 0 :=
  (quintuple a b c d e).preserves_orthogonality hxy

/-- Six certified geometry stages transport orthogonality. -/
theorem sextuple_preserves_orthogonality
    (a b c d e f : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    inner ℝ ((sextuple a b c d e f).toFun x)
      ((sextuple a b c d e f).toFun y) = 0 :=
  (sextuple a b c d e f).preserves_orthogonality hxy

/-- Seven certified geometry stages transport orthogonality. -/
theorem septuple_preserves_orthogonality
    (a b c d e f g : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    inner ℝ ((septuple a b c d e f g).toFun x)
      ((septuple a b c d e f g).toFun y) = 0 :=
  (septuple a b c d e f g).preserves_orthogonality hxy

/-- Eight certified geometry stages transport orthogonality. -/
theorem octuple_preserves_orthogonality
    (a b c d e f g h : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    inner ℝ ((octuple a b c d e f g h).toFun x)
      ((octuple a b c d e f g h).toFun y) = 0 :=
  (octuple a b c d e f g h).preserves_orthogonality hxy

/-- Nine certified geometry stages transport orthogonality. -/
theorem nonuple_preserves_orthogonality
    (a b c d e f g h i : CertifiedGeometryTransform E) {x y : E}
    (hxy : inner ℝ x y = 0) :
    inner ℝ ((nonuple a b c d e f g h i).toFun x)
      ((nonuple a b c d e f g h i).toFun y) = 0 :=
  (nonuple a b c d e f g h i).preserves_orthogonality hxy

/-- Compose an arbitrary ranked transform list. -/
def chain : List (CertifiedGeometryTransform E) → CertifiedGeometryTransform E
  | [] => identity
  | f :: fs => comp f (chain fs)

/-- Sum of the abstract costs attached to a transform list. -/
def totalCost (fs : List (CertifiedGeometryTransform E)) : Nat :=
  (fs.map fun f => f.cost).sum

@[simp] theorem chain_nil :
    (chain ([] : List (CertifiedGeometryTransform E))).cost = 0 := rfl

@[simp] theorem chain_cons_cost
    (f : CertifiedGeometryTransform E)
    (fs : List (CertifiedGeometryTransform E)) :
    (chain (f :: fs)).cost = f.cost + (chain fs).cost := rfl

/-- Arbitrary composition has exactly the sum of the component costs. -/
theorem chain_cost (fs : List (CertifiedGeometryTransform E)) :
    (chain fs).cost = totalCost fs := by
  induction fs with
  | nil =>
      rfl
  | cons f fs ih =>
      simp [chain, totalCost, ih, Nat.add_assoc]

/-- A transform list certified below a budget stays below the same budget after
composition.  This is the cheap pruning lemma used by future ranked searches. -/
theorem chain_within_budget
    (fs : List (CertifiedGeometryTransform E)) (budget : Nat)
    (hbudget : totalCost fs ≤ budget) :
    (chain fs).cost ≤ budget := by
  simpa [chain_cost fs] using hbudget

end CertifiedGeometryTransform

end

end CACEFormal
