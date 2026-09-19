import Mathlib.Data.Nat.Basic

namespace CACEFormal

universe u v

/-!
# Cheap certified transform composition

This file is intentionally generic and algebraic.  It lets CACE combine two,
three, four, or more proof-preserving transforms without reproving the invariant
at every call site.  `staticCost` is declared metadata only; it is not a timing
claim and must not be confused with measured runtime.
-/

/-- A state transform together with a proof that it preserves one invariant. -/
structure CertifiedTransform (α : Type u) (Invariant : α → Prop) where
  run : α → α
  staticCost : Nat
  preserves : ∀ x, Invariant x → Invariant (run x)

namespace CertifiedTransform

/-- Identity transform with zero declared static cost. -/
def identity {α : Type u} (Invariant : α → Prop) : CertifiedTransform α Invariant where
  run := id
  staticCost := 0
  preserves := by
    intro x hx
    exact hx

/-- Sequential composition.  `inner` runs first and `outer` runs second. -/
def comp {α : Type u} {Invariant : α → Prop}
    (outer inner : CertifiedTransform α Invariant) : CertifiedTransform α Invariant where
  run := fun x => outer.run (inner.run x)
  staticCost := inner.staticCost + outer.staticCost
  preserves := by
    intro x hx
    exact outer.preserves (inner.run x) (inner.preserves x hx)

@[simp] theorem identity_run {α : Type u} {Invariant : α → Prop} (x : α) :
    (identity Invariant).run x = x := rfl

@[simp] theorem identity_staticCost {α : Type u} {Invariant : α → Prop} :
    (identity Invariant).staticCost = 0 := rfl

@[simp] theorem comp_run {α : Type u} {Invariant : α → Prop}
    (outer inner : CertifiedTransform α Invariant) (x : α) :
    (comp outer inner).run x = outer.run (inner.run x) := rfl

@[simp] theorem comp_staticCost {α : Type u} {Invariant : α → Prop}
    (outer inner : CertifiedTransform α Invariant) :
    (comp outer inner).staticCost = inner.staticCost + outer.staticCost := rfl

/-- Two transforms, evaluated left-to-right: `t1`, then `t2`. -/
def compose2 {α : Type u} {Invariant : α → Prop}
    (t1 t2 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t2 t1

/-- Three transforms, evaluated left-to-right. -/
def compose3 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t3 (compose2 t1 t2)

/-- Four transforms, evaluated left-to-right. -/
def compose4 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t4 (compose3 t1 t2 t3)

/-- Any certified two-stage combination preserves the shared invariant. -/
theorem compose2_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose2 t1 t2).run x) :=
  (compose2 t1 t2).preserves x hx

/-- Any certified three-stage combination preserves the shared invariant. -/
theorem compose3_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose3 t1 t2 t3).run x) :=
  (compose3 t1 t2 t3).preserves x hx

/-- Any certified four-stage combination preserves the shared invariant. -/
theorem compose4_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose4 t1 t2 t3 t4).run x) :=
  (compose4 t1 t2 t3 t4).preserves x hx

/--
Run two independent certified transforms in parallel on a product state.
This is the basic combinator for joining proof modules that do not share state.
-/
def product
    {α : Type u} {β : Type v} {P : α → Prop} {Q : β → Prop}
    (left : CertifiedTransform α P) (right : CertifiedTransform β Q) :
    CertifiedTransform (α × β) (fun x => P x.1 ∧ Q x.2) where
  run := fun x => (left.run x.1, right.run x.2)
  staticCost := left.staticCost + right.staticCost
  preserves := by
    intro x hx
    exact ⟨left.preserves x.1 hx.1, right.preserves x.2 hx.2⟩

@[simp] theorem product_staticCost
    {α : Type u} {β : Type v} {P : α → Prop} {Q : β → Prop}
    (left : CertifiedTransform α P) (right : CertifiedTransform β Q) :
    (product left right).staticCost = left.staticCost + right.staticCost := rfl

end CertifiedTransform

end CACEFormal
