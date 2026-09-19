# CACE Molecular, Protein, Materials, and Physics Canvas Expansion

Status: research/engineering design. Not proof evidence, not clinical guidance, and not a guarantee of physical ground-state discovery.

Date: 2026-09-19

## 1. Goals

Add four interoperable capability families:

1. **Atoms and molecules** as typed canvas objects.
2. **Protein structure and folding demos** for user-supplied sequences/structures.
3. **Novel-material computational screening** driven by mathematical descriptors and explicit uncertainty.
4. **Physics objects** that can be dragged onto the canvas, including established Standard Model entities and clearly labeled theoretical constructs such as strings.

All four use the existing CACE evidence hierarchy and must preserve the distinction between visualization, numerical experiment, hypothesis generation, and formal proof.

## 2. AlphaFold licensing/integration policy

CACE should use AlphaFold only through license-compatible, attributable interfaces.

Current policy target:

- AlphaFold 2 source code: Apache-2.0.
- Published AlphaFold 2 parameters and AlphaFold DB prediction data: CC-BY-4.0 with attribution.
- AlphaFold 3 source: Apache-2.0, but model weights are governed by separate terms and therefore are **not bundled by default**.
- Third-party structure/model assets always carry source, license, attribution, version, and content hash metadata.
- CACE core must remain functional without AlphaFold installed.
- No AlphaFold trademarks/branding should imply affiliation or endorsement.

The first implementation should support importing externally generated AlphaFold-compatible structures rather than vendoring large model assets.

## 3. Protein structure versus protein design

AlphaFold predicts structure for a supplied sequence; it does not itself generate novel protein sequences.

CACE therefore separates:

- **sequence source**;
- **structure prediction/import**;
- **energy refinement/search**;
- **sequence design/search**.

The initial safe slice implements the first three only. Novel sequence design can be a later separately reviewed research feature.

## 4. Lowest-energy folding demo

The user-facing demo should say:

> Lowest energy found by this search

and never:

> global minimum / true native state proven.

Initial fast local backend:

- one C-alpha point per residue;
- fixed/penalized backbone spacing;
- short-range repulsion;
- weak hydrophobic-contact attraction;
- radius/compactness regularization;
- seeded pivot/rotation proposals;
- simulated annealing / stochastic descent;
- deterministic replay from seed;
- optional imported coordinates as the initial state.

Output:

- best coordinates found;
- best coarse energy;
- energy trace;
- seed;
- model/version;
- limitations;
- explicit `global_minimum_claim=false`.

Large proteins can later route to external/local AlphaFold/OpenMM-compatible backends while retaining the same typed contract.

## 5. AlphaFold structure import

First adapter:

- accept PDB text/file produced by AlphaFold or another compatible predictor;
- extract residue identity and C-alpha coordinates;
- preserve pLDDT/B-factor when present;
- store source URL/name only as metadata supplied by the user/import workflow;
- store license and attribution string;
- never mark imported predictions as experimental truth.

A later connector may fetch AlphaFold DB records, but the zero-egress scientific core should not require Internet access.

## 6. Atoms and molecules

Introduce typed scientific objects:

### Atom

Fields:

- element symbol;
- atomic number when known;
- isotope/mass number optional;
- formal charge;
- 3D position;
- provenance/evidence metadata.

### Bond

Fields:

- endpoint indices;
- bond order/type;
- optional confidence/source.

### Molecule

Fields:

- stable ID;
- atoms;
- bonds;
- total formal charge;
- optional geometry;
- optional formula/name;
- source/provenance;
- evidence class.

Canvas renderers can use ball-and-stick, space-filling, or graph views without changing the scientific object identity.

## 7. Safe home-lab chemistry

CACE may include a **Safe Home Lab** mode for low-risk educational activities using a strict whitelist.

Initial allowed examples:

- red-cabbage or similarly low-risk acid/base indicator observations;
- table-salt or sugar crystallization;
- solubility comparisons with household-safe materials;
- evaporation/temperature observations with ordinary kitchen-safe materials.

The module must not generate hazardous synthesis instructions, energetic chemistry, toxic-gas generation, pressure-vessel procedures, drug synthesis, explosive mixtures, or unsafe heating protocols.

Every experiment template includes:

- allowed materials;
- prohibited substitutions;
- PPE/common-sense cautions;
- disposal note;
- expected observable;
- measurement table schema;
- risk level.

Unsupported chemistry requests fail closed to a simulation-only path.

## 8. Novel materials search

The first implementation is a **hypothesis generator / screening engine**, not a synthesis planner.

Represent candidate materials as:

- composition/stoichiometry;
- structure family if supplied;
- elemental descriptor vector;
- optional lattice parameters;
- predicted/estimated properties with uncertainty;
- source of each property model.

Search can combine:

- atomic mass statistics;
- electronegativity spread;
- covalent/ionic radius mismatch;
- valence-electron statistics;
- composition entropy;
- symmetry/lattice descriptors;
- graph/spectral descriptors;
- user-supplied surrogate/property models.

CACE ranks candidates against target constraints and explains the mathematical reason for each score.

It must distinguish:

- measured property;
- database value;
- physics-based calculation;
- learned surrogate prediction;
- heuristic descriptor.

No candidate is called a discovered material until external evidence exists.

## 9. Physics canvas objects

Add typed draggable objects for:

### Established entities

- electron;
- muon/tau;
- neutrino flavors;
- up/down/strange/charm/top/bottom quarks;
- photon;
- gluon;
- W/Z bosons;
- Higgs boson.

Fields can include charge, spin, mass/reference value, interaction labels, and provenance.

Important rendering rule:

- quarks are visualized as model entities and should include a confinement note rather than implying free isolated quarks are laboratory objects.

### Theoretical/research objects

- string segment/mode;
- brane-like object;
- generic field;
- worldline/worldsheet;
- abstract symmetry generator.

These must be explicitly labeled **theoretical/research visualization**, not established physical detections.

## 10. Canvas interoperability

Typed ports should allow useful connections such as:

- ProteinSequence -> StructureImport/Predictor -> CoarseFoldSearch -> GeometryViewer
- Molecule -> PropertyCalculator -> MaterialCandidateSearch
- AtomSet -> MoleculeBuilder
- PhysicsObject -> Transform/Rotation/FieldViewer
- MaterialCandidate -> ResearchIdea -> ProposedExperiment

The canvas UI can render special icons/shapes while the underlying scientific semantics remain typed objects.

## 11. Safety and evidence

Hard rules:

- protein/chemistry/material outputs are research/numerical unless an appropriate verifier establishes more;
- predicted protein structures are not clinical evidence;
- low energy found is not proof of a protein's native/global minimum conformation;
- material-property heuristics are not synthesis guarantees;
- home-lab mode is safe-whitelist only;
- theoretical physics objects remain labeled theoretical;
- third-party licenses/attributions are preserved in exported artifacts.

## 12. First executable slice

1. Atom/Bond/Molecule dataclasses.
2. ProteinSequence + ProteinStructure dataclasses.
3. PDB C-alpha importer with attribution metadata.
4. Deterministic coarse protein folding/energy search.
5. SafeHomeExperiment registry with whitelist/fail-closed behavior.
6. MaterialCandidate + descriptor-based screening.
7. PhysicsCanvasObject catalog with established/theoretical classification.
8. CACE module wrappers and registry integration.
9. Tests for:
   - deterministic fold replay;
   - no global-minimum claim;
   - AlphaFold attribution metadata preservation;
   - home-lab whitelist enforcement;
   - material score reproducibility;
   - theoretical physics labels;
   - typed object round trips.


## 13. Baseline implementation status

Branch: `feature/molecular-materials-physics`

The first executable slice includes:

- all 118 element symbols as typed Atom identities;
- typed Bond and Molecule objects with deterministic formula/JSON rendering;
- a `Protein Sequence` source node;
- an AlphaFold-compatible C-alpha PDB importer preserving source, license, attribution, confidence, and content hash metadata;
- a deterministic seeded C-alpha fold search with bond/clash/hydrophobic/compactness terms;
- the hard output guard `global_minimum_claim=false`;
- a strict low-risk Safe Home Lab whitelist;
- deterministic descriptor-based materials candidate ranking with no synthesis instructions;
- established-vs-theoretical physics canvas objects including all six quark flavors and string/worldsheet/brane research objects;
- registry integration so the objects appear as normal CACE canvas modules;
- regression tests for determinism, attribution, safety, evidence labeling, and nonclaims.

This baseline does **not** bundle AlphaFold code, databases, or model weights.
