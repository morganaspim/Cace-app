import Mathlib.Data.List.Basic
import Mathlib.Data.Nat.Basic

namespace CACEFormal

universe u v

/-!
# Cheap certified transform composition

This file is intentionally generic and algebraic. It lets CACE combine two,
three, four, or arbitrarily many proof-preserving transforms without reproving
the invariant at every call site. `staticCost` is declared metadata only; it is
not a timing claim and must not be confused with measured runtime.
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

/-- Sequential composition. `inner` runs first and `outer` runs second. -/
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

/-- Five transforms, evaluated left-to-right. -/
def compose5 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t5 (compose4 t1 t2 t3 t4)

/-- Six transforms, evaluated left-to-right. -/
def compose6 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t6 (compose5 t1 t2 t3 t4 t5)

/-- Seven transforms, evaluated left-to-right. -/
def compose7 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t7 (compose6 t1 t2 t3 t4 t5 t6)

/-- Eight transforms, evaluated left-to-right. -/
def compose8 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 t8 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t8 (compose7 t1 t2 t3 t4 t5 t6 t7)

/-- Nine transforms, evaluated left-to-right. -/
def compose9 {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 t8 t9 : CertifiedTransform α Invariant) : CertifiedTransform α Invariant :=
  comp t9 (compose8 t1 t2 t3 t4 t5 t6 t7 t8)

/-- Any certified five-stage combination preserves the shared invariant. -/
theorem compose5_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose5 t1 t2 t3 t4 t5).run x) :=
  (compose5 t1 t2 t3 t4 t5).preserves x hx

/-- Any certified six-stage combination preserves the shared invariant. -/
theorem compose6_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose6 t1 t2 t3 t4 t5 t6).run x) :=
  (compose6 t1 t2 t3 t4 t5 t6).preserves x hx

/-- Any certified seven-stage combination preserves the shared invariant. -/
theorem compose7_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose7 t1 t2 t3 t4 t5 t6 t7).run x) :=
  (compose7 t1 t2 t3 t4 t5 t6 t7).preserves x hx

/-- Any certified eight-stage combination preserves the shared invariant. -/
theorem compose8_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 t8 : CertifiedTransform α Invariant) (x : α) (hx : Invariant x) :
    Invariant ((compose8 t1 t2 t3 t4 t5 t6 t7 t8).run x) :=
  (compose8 t1 t2 t3 t4 t5 t6 t7 t8).preserves x hx

/-- Any certified nine-stage combination preserves the shared invariant. -/
theorem compose9_preserves {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 t8 t9 : CertifiedTransform α Invariant) (x : α)
    (hx : Invariant x) :
    Invariant ((compose9 t1 t2 t3 t4 t5 t6 t7 t8 t9).run x) :=
  (compose9 t1 t2 t3 t4 t5 t6 t7 t8 t9).preserves x hx

@[simp] theorem compose5_staticCost {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 : CertifiedTransform α Invariant) :
    (compose5 t1 t2 t3 t4 t5).staticCost =
      ((((t1.staticCost + t2.staticCost) + t3.staticCost) + t4.staticCost) + t5.staticCost) := rfl

@[simp] theorem compose6_staticCost {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 : CertifiedTransform α Invariant) :
    (compose6 t1 t2 t3 t4 t5 t6).staticCost =
      (((((t1.staticCost + t2.staticCost) + t3.staticCost) + t4.staticCost) +
        t5.staticCost) + t6.staticCost) := rfl

@[simp] theorem compose7_staticCost {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 : CertifiedTransform α Invariant) :
    (compose7 t1 t2 t3 t4 t5 t6 t7).staticCost =
      ((((((t1.staticCost + t2.staticCost) + t3.staticCost) + t4.staticCost) +
        t5.staticCost) + t6.staticCost) + t7.staticCost) := rfl

@[simp] theorem compose8_staticCost {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 t8 : CertifiedTransform α Invariant) :
    (compose8 t1 t2 t3 t4 t5 t6 t7 t8).staticCost =
      (((((((t1.staticCost + t2.staticCost) + t3.staticCost) + t4.staticCost) +
        t5.staticCost) + t6.staticCost) + t7.staticCost) + t8.staticCost) := rfl

@[simp] theorem compose9_staticCost {α : Type u} {Invariant : α → Prop}
    (t1 t2 t3 t4 t5 t6 t7 t8 t9 : CertifiedTransform α Invariant) :
    (compose9 t1 t2 t3 t4 t5 t6 t7 t8 t9).staticCost =
      ((((((((t1.staticCost + t2.staticCost) + t3.staticCost) + t4.staticCost) +
        t5.staticCost) + t6.staticCost) + t7.staticCost) + t8.staticCost) +
        t9.staticCost) := rfl

/-- Compose an arbitrary list left-to-right. This is the scalable 9+ endpoint. -/
def composeList {α : Type u} {Invariant : α → Prop} :
    List (CertifiedTransform α Invariant) → CertifiedTransform α Invariant
  | [] => identity Invariant
  | t :: ts => comp (composeList ts) t

/-- Sum of declared costs for a proposed transform list. -/
def totalStaticCost {α : Type u} {Invariant : α → Prop}
    (ts : List (CertifiedTransform α Invariant)) : Nat :=
  (ts.map fun t => t.staticCost).sum

@[simp] theorem composeList_nil {α : Type u} {Invariant : α → Prop} :
    (composeList ([] : List (CertifiedTransform α Invariant))).staticCost = 0 := rfl

@[simp] theorem composeList_cons_staticCost {α : Type u} {Invariant : α → Prop}
    (t : CertifiedTransform α Invariant) (ts : List (CertifiedTransform α Invariant)) :
    (composeList (t :: ts)).staticCost = t.staticCost + (composeList ts).staticCost := rfl

/-- Arbitrary composition preserves the shared invariant by construction. -/
theorem composeList_preserves {α : Type u} {Invariant : α → Prop}
    (ts : List (CertifiedTransform α Invariant)) (x : α) (hx : Invariant x) :
    Invariant ((composeList ts).run x) :=
  (composeList ts).preserves x hx

/-- The composed certificate carries exactly the sum of the declared costs. -/
theorem composeList_staticCost {α : Type u} {Invariant : α → Prop}
    (ts : List (CertifiedTransform α Invariant)) :
    (composeList ts).staticCost = totalStaticCost ts := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
      simp [composeList, totalStaticCost, ih]

/-- A planner may prune candidates using a budget without participating in the
mathematical trust boundary: any selected certified list remains invariant-safe. -/
theorem composeList_withinBudget {α : Type u} {Invariant : α → Prop}
    (ts : List (CertifiedTransform α Invariant)) (budget : Nat)
    (hbudget : totalStaticCost ts ≤ budget) :
    (composeList ts).staticCost ≤ budget := by
  rw [composeList_staticCost]
  exact hbudget

/-- If every selected stage has declared cost at least one, then the number
of selected stages is bounded by the declared total cost.  This is a formal
combinatorial pruning fact; it still makes no wall-clock runtime claim. -/
theorem length_le_totalStaticCost_of_positive
    {α : Type u} {Invariant : α → Prop}
    (ts : List (CertifiedTransform α Invariant))
    (hpositive : ∀ t ∈ ts, 1 ≤ t.staticCost) :
    ts.length ≤ totalStaticCost ts := by
  induction ts with
  | nil =>
      simp [totalStaticCost]
  | cons t ts ih =>
      have ht : 1 ≤ t.staticCost := hpositive t (by simp)
      have htail : ∀ s ∈ ts, 1 ≤ s.staticCost := by
        intro s hs
        exact hpositive s (by simp [hs])
      have hi := ih htail
      have hadd := Nat.add_le_add ht hi
      simpa [totalStaticCost, Nat.add_comm] using hadd

/-- Under positive per-stage declared costs, any chain admitted by a budget has
length at most that budget. -/
theorem length_le_budget_of_positive
    {α : Type u} {Invariant : α → Prop}
    (ts : List (CertifiedTransform α Invariant)) (budget : Nat)
    (hpositive : ∀ t ∈ ts, 1 ≤ t.staticCost)
    (hbudget : totalStaticCost ts ≤ budget) :
    ts.length ≤ budget :=
  le_trans (length_le_totalStaticCost_of_positive ts hpositive) hbudget

/-- A generic floor theorem for 5+, 6+, 7+, 8+, 9+, or any later group size:
if a positively-costed certified chain has at least `n` stages and fits within
a declared budget, then that budget is at least `n`. -/
theorem groupSize_le_budget_of_positive
    {α : Type u} {Invariant : α → Prop}
    (n : Nat) (ts : List (CertifiedTransform α Invariant)) (budget : Nat)
    (hsize : n ≤ ts.length)
    (hpositive : ∀ t ∈ ts, 1 ≤ t.staticCost)
    (hbudget : totalStaticCost ts ≤ budget) :
    n ≤ budget :=
  le_trans hsize (length_le_budget_of_positive ts budget hpositive hbudget)

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
