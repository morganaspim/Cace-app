# CACE Source-to-Formal Linkage Specification

Status: implementation specification and proof-obligation map. It is **not** proof evidence and does not claim the listed missing links are already established.

Date: 2026-09-19.

## 1. Goal

Establish an auditable chain from concrete CACE runtime/finite-element data to the exact Lean hypotheses consumed by discrete and continuum theorems.

The target is not merely:

`runtime result -> theorem name`

The target is:

`runtime object -> exact representation identity -> Lean object -> theorem hypotheses -> qualified theorem endpoint -> fail-closed runtime evidence`

No step may be skipped or inferred from similarity.

## 2. Existing anchors

### Runtime / governance anchors

- `cace_studio/modules/formal_hypothesis_bridges.py`
  - already demonstrates a fail-closed runtime/formal pattern;
  - the current exact-zero bridge binds only an exact zero runtime vector to `HasZeroBoundaryTrace G 0`;
  - it deliberately leaves unrelated Prager-Synge premises unresolved.
- `cace_studio/core/proof_contract.py`
- `cace_studio/core/formal_gate.py`
- `cace_studio/data/proof_contracts.json`
- `cace_studio/data/claim_registry.json`
- `cace_studio/data/proof_ledger.json`

### Exact/discrete Lean anchors

- `CACEFormal.P1RT0Element`
  - exact affine P1 scalar and RT0 vector representations;
  - exact local cell, divergence, and face pairings;
  - exact local Green identity.
- `CACEFormal.PhysicalP1RT0Element`
  - positive-orientation physical interpretation.
- `CACEFormal.MeshCertificate`
- `CACEFormal.MeshElementGeometry`
- `CACEFormal.MeshFaceAssembly`
- `CACEFormal.RT0P1DerivedAssembly`
  - global assembly from local Green identity plus equilibrium, boundary admissibility, and interior cancellation.
- `CACEFormal.DiscreteOrthogonality`
- `CACEFormal.DiscretePragerSynge`

### Continuum Lean anchors

- `CACEFormal.ContinuumGraphSpaces`
- `CACEFormal.GraphClosedSpaces`
- `CACEFormal.GraphGreenPairing`
- `CACEFormal.BoxGraphGreenPairing`
- `CACEFormal.BoxGraphTrace`
- `CACEFormal.BoxClassicalAgreement`
- `CACEFormal.SmoothBoxGreen`
- `CACEFormal.WeakGreenFunctional`
- `CACEFormal.ContinuumOrthogonality`
- `CACEFormal.ContinuumPragerSynge`
- current v3.41 theorem roadmap for constructing concrete zero-boundary box graph data.

## 3. Current explicit nonclaim

CACE must continue to state:

> Exact P1/RT0 finite-element identities and qualified continuum theorems do not by themselves prove that arbitrary Python/C++ runtime finite-element fields inhabit the required continuum H1/H(div) graph spaces or satisfy the continuum Green/trace hypotheses.

This linkage is exactly what this specification is intended to close.

## 4. Two linkage lanes

### Lane A — exact discrete linkage

Purpose: bind runtime mesh/P1/RT0 data to the exact finite Lean objects and discrete theorems.

### Lane B — continuum graph linkage

Purpose: embed or relate appropriate concrete fields to the bounded-box H1/H(div) graph objects and their `volumePairing` / normal-trace hypotheses.

Lane A can become useful before Lane B is complete. Do not claim Lane B from Lane A.

## 5. Obligation ladder

### FSL-0 — Canonical runtime packet

Define a versioned, deterministic runtime packet containing:

- mesh vertices/connectivity;
- orientation/ownership data;
- P1 coefficients per cell;
- RT0 coefficients per cell;
- boundary/interior face mapping;
- exact or explicitly encoded numeric representation;
- source module/version;
- semantic hash;
- packet SHA-256.

Acceptance:
- deterministic serialization;
- malformed/missing/nonfinite data rejected;
- packet identity changes when any mathematical datum changes.

### FSL-1 — Exact numeric representation policy

Choose and document the bridge representation.

Preferred production paths:

1. exact rationals/integers when runtime inputs are exact;
2. generated Lean literals from canonical rational data;
3. if floating-point input is used, do **not** silently reinterpret it as exact real equality.

Floating-point paths must either:
- produce a separate interval/certified enclosure claim; or
- remain numerical and unresolved for exact formal instantiation.

Acceptance:
- no tolerance-based equality may discharge an exact Lean premise.

### FSL-2 — Runtime mesh -> `MeshCertificate`

Construct a generated/exact Lean mesh certificate from the canonical packet, or prove a checker theorem that reconstructs the same object.

Must bind:

- triangle count;
- exact coordinates;
- connectivity;
- edge ownership;
- positive orientation/signed Jacobian requirements;
- boundary/interior partition.

Relevant Lean anchors:
- `MeshCertificate.lean`
- `MeshElementGeometry.lean`
- `MeshFaceAssembly.lean`
- `ConcreteMeshCertificate.lean`
- generated certificate patterns under `CACEFormal/Generated/`.

Acceptance:
- exact packet hash is recorded in generated-source metadata;
- changing runtime geometry invalidates the generated binding.

### FSL-3 — Runtime P1 coefficients -> `P1Affine`

For every cell K, bind runtime scalar coefficients exactly to:

`P1Affine { c, gx, gy }`.

Acceptance:
- dimension/cardinality checked;
- coefficient order fixed and versioned;
- no sampled-value reconstruction unless separately proved equivalent.

### FSL-4 — Runtime RT0 coefficients -> `RT0Affine`

For every cell K, bind runtime flux coefficients exactly to:

`RT0Affine { cx, cy, radial }`.

Acceptance:
- exact coefficient identity;
- RT0 convention/version recorded;
- no alternate basis accepted without a proved basis transform.

### FSL-5 — Exact local semantics

Instantiate:

- `P1RT0Element.cellPairing`;
- `P1RT0Element.cellDivergence`;
- `P1RT0Element.localFacePairing`;
- `P1RT0Element.local_green_identity`.

For certified positive geometry, connect to:
- `PhysicalP1RT0Element.mesh_local_green_identity`.

Acceptance:
- runtime-computed exact quantities either match generated Lean evaluation exactly or are treated only as non-formal cache/display values.

### FSL-6 — Exact global assembly

Use the certified mesh and exact element data to instantiate:
- `RT0P1DerivedAssemblyCertificate.ofCertifiedMeshElements`.

The remaining physical hypotheses must be supplied explicitly:
- equilibrium;
- boundary admissibility;
- interior cancellation.

Acceptance:
- each hypothesis has its own certificate/status;
- a missing one remains unresolved;
- `RT0P1DerivedAssemblyCertificate.orthogonality` is consumed only after all required hypotheses are proved for the concrete object.

### FSL-7 — Discrete Prager-Synge endpoint binding

Bind the exact concrete assembly object to the appropriate discrete orthogonality / Prager-Synge theorem.

Acceptance:
- theorem endpoint is in the exact proof contract;
- canonical qualification gate passes;
- runtime bridge certificate records theorem name, contract hash, attested commit, artifact digest, and packet hash.

At completion of FSL-0..7, CACE may make exact **discrete** claims within the theorem's real scope. This still does not establish the continuum graph-space premises.

## 6. Continuum bridge obligations

### FSL-8 — Concrete scalar field -> bounded-box H1 graph datum

Define a Lean construction connecting the concrete piecewise P1 scalar field to the bounded-box H1 graph representation actually used by CACE's continuum theory.

Required facts must include, as applicable:

- measurable/L2 representative;
- weak/distributional gradient relation;
- integrability;
- correct domain restriction;
- interface compatibility needed for global H1 membership.

Do not replace these with sampled continuity checks.

Acceptance:
- an explicit theorem returns the exact closed graph-space datum or a membership proof;
- theorem hypotheses are traceable to the runtime packet.

### FSL-9 — Concrete RT0 field -> bounded-box H(div) graph datum

Define the corresponding construction for the assembled RT0 field.

Required facts must include, as applicable:

- L2 vector representative;
- distributional divergence;
- integrability;
- interface normal-trace cancellation needed for global H(div);
- correct boundary/domain restriction.

Acceptance:
- an explicit theorem returns the exact closed H(div) graph datum or membership proof.

### FSL-10 — Finite assembly pairing -> continuum `volumePairing`

Prove that the concrete finite sum used by the exact P1/RT0 assembly equals the continuum graph Green-pairing volume term for the embedded concrete fields.

This is a load-bearing bridge.

It must connect the discrete object actually computed to the exact `volumePairing` consumed by the continuum weak-Green/orthogonality chain.

Acceptance:
- equality theorem in Lean;
- no numerical quadrature assumption unless represented explicitly;
- no prose-only identification of the two pairings.

### FSL-11 — Boundary/normal-trace bridge

Connect concrete boundary conditions to the functional normal-trace predicate used by the continuum theory.

The v3.41 program is the preferred safe route for H1-zero box data:
- explicit smooth face-vanishing core;
- classical face cancellation;
- continuity/density extension;
- closed graph-space zero-boundary object.

For finite-element P1 boundary data, a separate theorem may be needed to show membership in the chosen zero-boundary graph space or pairwise trace cancellation.

Acceptance:
- exact theorem discharges the boundary premise actually consumed;
- do not prove/require a stronger global predicate when a pairwise theorem suffices unless needed elsewhere.

### FSL-12 — Cross-term identification

For the concrete primal/flux errors, prove that the continuum cross term used by Prager-Synge is exactly the `volumePairing` (or other pairing) already connected in FSL-10.

Acceptance:
- explicit theorem;
- exact signs/conventions documented;
- regression theorem for orientation/sign mistakes.

### FSL-13 — Concrete continuum endpoint

Only after FSL-8..12 are complete may CACE instantiate the continuum orthogonality/Prager-Synge endpoint for the concrete runtime-derived fields.

Acceptance:
- all theorem hypotheses are marked pass by explicit bridge certificates;
- no unresolved hypothesis remains;
- canonical proof contract and qualification gate pass;
- packet-to-Lean source binding is content addressed.

## 7. Runtime bridge certificate shape

New bridge code should follow the fail-closed design already demonstrated by `formal_hypothesis_bridges.py`.

A bridge certificate should contain at least:

- schema/version;
- claim ID;
- theorem name;
- premise ID;
- runtime packet SHA-256;
- representation/binding method;
- generated Lean source hash when applicable;
- exact formal instantiation summary;
- proof-contract ID/hash;
- qualification anchor;
- state: pass / fail / not-qualified / unresolved;
- scope note;
- certificate SHA-256.

A resolver may discharge only the exact premise named by that certificate.

## 8. Proposed implementation files

Prefer strengthening canonical subsystems instead of creating many version wrappers.

Suggested runtime additions:

- `cace_studio/core/formal_runtime_packet.py`
  - canonical packet types, hashing, validation.
- `cace_studio/core/formal_source_binding.py`
  - generated-source identity and packet/source binding.
- `cace_studio/modules/p1_rt0_formal_bridges.py`
  - FSL-2..7 runtime bridge modules/resolvers.
- later, only after Lean theorems exist:
  - continuum bridge modules for FSL-8..13.

Suggested formal additions should be named by mathematical purpose, not version number. Candidate modules:

- `RuntimeP1RT0Binding.lean`
- `PiecewiseP1H1Bridge.lean`
- `PiecewiseRT0HDivBridge.lean`
- `P1RT0VolumePairingBridge.lean`
- `ConcreteP1RT0PragerSynge.lean`

Names are proposals, not claims that these files exist.

## 9. Tests required

### Runtime tests

- canonical packet determinism;
- one-bit/one-coefficient changes alter hash;
- malformed geometry rejected;
- orientation mismatch rejected;
- coefficient reordering rejected;
- near-zero does not satisfy exact-zero bridges;
- stale proof contract rejected;
- stale qualification rejected;
- tampered certificate rejected;
- unresolved premises remain unresolved.

### Formal tests/guardrails

- generated exact instance compiles;
- changed packet cannot reuse old generated binding;
- local and global sign conventions have regression theorems;
- theorem metadata includes every promoted endpoint;
- kernel axiom audit remains clean;
- proof-contract endpoint equality is exact;
- no `sorry`/unfinished tokens;
- reverse dependents compile.

## 10. Qualification flow

For each new Lean bridge module:

1. develop in quarantine;
2. run local/static/source sanity;
3. run standalone Exact-Pin with `compile_root=false`;
4. fix the complete discovered failure class;
5. add regression guards;
6. promote imports + axiom audit + theorem metadata + proof contract atomically;
7. run audited-root Exact-Pin;
8. run one canonical exact-current-head qualification;
9. accept provenance only for the exact earned source/artifact binding.

For multiple ready bridge modules, use the existing batched preflight where appropriate to minimize user dispatches without weakening qualification.

## 11. Milestone ordering

### Milestone 1 — builder-safe foundation

- land `CACE_AI_BUILDER_CONTRACT.md`;
- land this linkage specification;
- expose both in agent/bootstrap navigation;
- record durable goals.

### Milestone 2 — exact discrete packet and binding

Implement FSL-0..4 with tests. No new formal public claim yet.

### Milestone 3 — concrete discrete theorem instantiation

Implement FSL-5..7 and qualify the exact discrete runtime bridge.

### Milestone 4 — continuum representation theorems

Implement FSL-8..10, preserving all current nonclaims until qualified.

### Milestone 5 — boundary and cross-term closure

Implement FSL-11..12, integrating the strongest already-qualified v3.41 boundary results.

### Milestone 6 — concrete continuum Prager-Synge

Implement and qualify FSL-13.

## 12. Stop conditions

Stop promotion and leave the premise unresolved if:

- runtime data cannot be represented exactly under the chosen policy;
- a mesh/topology/orientation invariant is missing;
- a required H1/H(div) membership theorem is absent;
- discrete and continuum pairing equality has not been proved;
- theorem metadata/contract identity is stale;
- canonical qualification is absent or fails;
- source drift invalidates the attestation.

The correct state for an unproved bridge is **unresolved/NOT_RUN**, not an optimistic PASS.
