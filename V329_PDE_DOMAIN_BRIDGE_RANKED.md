# CACE v3.29 — PDE/domain bridge ranked implementation plan

## Scope

v3.29 is the bridge between the abstract/closure-level continuum machinery proved through v3.28 and the PDE objects needed to interpret that machinery analytically.

The two target identifications are deliberately kept separate:

1. identify the closure-level functional normal trace with the classical signed box face-flux trace on a common dense smooth core and then by continuity;
2. tie graph data `(q, div q)` to the genuine distributional `H(div)` predicate, rather than treating graph coordinates as an independent certificate.

A result is counted as formal only after the pinned Lean/mathlib workflow passes. No theorem below is intended to identify a whole-space graph closure with a bounded-box space without an explicit restriction/extension theorem.

## Goal A — closure-level functional trace ↔ classical box face flux

### Rank 1 — bounded-box graph closure and smooth-core agreement

**Why first:** this is the most direct mathematical realization of the desired theorem and avoids pretending that a whole-space Schwartz closure is already a boundary-value space.

Implementation target:

- define box-restricted `L²` graph data using `volume.restrict (Set.Icc a b)`;
- define smooth scalar/vector graph maps on the box;
- define the box Green volume pairing as a continuous bilinear functional;
- use `CACEFormal.Continuum.smoothBoxGreen` / `smoothBoxNormalTrace` to prove agreement with signed face flux on the smooth core;
- define the closure trace by continuous extension and prove uniqueness from dense-core agreement.

**Success criterion:** a machine-checked theorem that the continuous closure trace is the unique extension of the classical signed face-flux functional on the chosen box smooth core.

### Rank 2 — whole-space → box restriction bridge

**Why second:** it would connect the already-built whole-space graph closure to the bounded-box model, but it is analytically more delicate because distributional derivatives of zero extensions acquire boundary terms.

Implementation target:

- construct a continuous restriction map at the `L²` graph-data level where the pinned Mathlib APIs support it;
- prove compatibility on smooth fields;
- explicitly distinguish restriction from zero extension;
- transfer the Green pairing only after derivative compatibility is proved.

**Success criterion:** an explicit commuting diagram from the existing whole-space smooth graph core into the bounded-box graph core.

### Rank 3 — dense-core uniqueness as the final identification step

**Why third:** this is high leverage once Rank 1 or Rank 2 supplies a common space and common dense core; by itself it cannot manufacture that domain bridge.

Implemented reusable theorem:

- `normalTrace_eq_of_classicalCoreAgreement`

It reduces the final trace equality to continuity plus equality on dense smooth cores.

## Goal B — graph closure ↔ distributional `H(div)`

### Rank 1 — closed distributional graph relation in complex `L²`

**Why first:** the distributional derivative is already a continuous linear operator on tempered distributions in pinned Mathlib, and `L²` embeds continuously into tempered distributions. Therefore the equation `div q = g` is naturally a closed kernel condition.

Implemented/in progress in `CACEFormal/PDEDomainBridge.lean`:

- `ComplexL2`;
- `HDivComplexGraphAmbient`;
- `complexL2ToDistribution`;
- `weakPartialCLM`;
- `complexHDivGraphDefect`;
- `HDivDistributionalGraphSubmodule`;
- `mem_HDivDistributionalGraphSubmodule_iff`;
- `isClosed_HDivDistributionalGraphSubmodule`;
- `complexL2ToDistribution_inL2`;
- `inHDiv_of_mem_distributionalGraph`.

Next theorem target:

- prove the complex Schwartz `H(div)` graph core lies in `HDivDistributionalGraphSubmodule` using Mathlib's derivative/tempered-distribution compatibility;
- conclude that the entire topological closure lies in the closed distributional graph relation.

**Success criterion:** every element of the smooth graph closure has an actual distributional divergence represented by its `L²` divergence coordinate and therefore satisfies `InHDiv`.

### Rank 2 — complexify the existing real v3.28 graph model

**Why second:** v3.28's graph closure is real-valued, while the current Sobolev/tempered-distribution interface uses complex-valued distributions. An explicit complexification map is the cleanest way to avoid silently identifying these scalar fields.

Implementation target:

- use `Complex.ofRealCLM`/the relevant `Lp` map to embed real `L²` graph coordinates into complex `L²`;
- prove compatibility with Schwartz graph maps and coordinate derivatives;
- extend continuously to the real graph closure;
- compose with Rank 1 to obtain a formal real-graph-closure → distributional-`H(div)` theorem.

**Success criterion:** a theorem beginning with `q : HDivGraphClosedSpace n`, not a separately constructed complex graph datum, and ending with a genuine distributional `InHDiv` statement for its canonical complex image.

### Rank 3 — reverse inclusion by graph-norm density/mollification

**Why third:** this is the strongest result—equality rather than one-way inclusion—but requires a genuine approximation theorem for arbitrary distributional `H(div)` fields.

Implementation target:

- choose a precise domain scope (whole space first; box separately);
- prove smooth/mollified approximation in both component `L²` norm and divergence `L²` norm;
- derive surjectivity onto the distributional graph relation;
- only then state graph closure = distributional `H(div)`.

**Success criterion:** two-sided equivalence, not merely an embedding. Until this is proved, v3.29 must state the direction actually formalized.

## Current theorem bridge

The current implementation also exposes:

- `smoothBoxTrace_eq_greenVolume`: classical box signed face flux equals the smooth Green volume integral under the already formalized box-divergence hypotheses;
- `normalTrace_eq_of_classicalCoreAgreement`: continuous normal traces agreeing on common dense smooth cores are identical.

Together these are the two endpoints needed for Goal A. The missing middle is the bounded-box graph-space construction/common dense-core map.

## Claim discipline

v3.29 must not claim any of the following until Lean proves them:

- that the existing whole-space `graphNormalTrace` already equals classical box face flux;
- that zero extension from a box commutes with distributional divergence without a boundary contribution;
- that the real v3.28 graph closure and the complex distributional graph relation are definitionally the same space;
- that every distributional `H(div)` field lies in the smooth graph closure without a graph-norm density theorem.

The intended closure chain is:

`v3.28 closed graph model`
→ `closed distributional divergence relation`
→ `smooth-core inclusion`
→ `closure inclusion into true H(div)`
→ `bounded-box graph model`
→ `classical face-flux agreement on smooth core`
→ `unique continuous trace extension`
→ `PDE-domain weak Green / Prager–Synge interpretation`.
