# CACE-KSEE Matter + Shape Toolbox

Status: production integration contract. Engineering capability evidence only; not formal proof.

## Purpose

CACE-KSEE should let users and the local AI place mathematical/geometric objects
directly on Canvas and connect qualified operations to them.

The first qualified object family includes:

### 2D

- Circle
- Parabola
- General conic
- Hyperbola

### 3D / N-D

- Sphere
- Hypercube (2D through 8D object, with renderer projection as needed)

### Chemistry geometry

- Atom / element-labelled point object
- Molecular graph built by joining atoms/molecular objects with labelled bonds

### Actions

- Explicit affine transform of any compatible geometric object

## Object contract

All of these emit:

`type_name = geometric_object`

with the envelope:

```text
cace-geometric-object-v1
  object_type
  geometry_kind
  dimension
  canonical parameters / points
  applied transforms
  evidence_authority = false
  proof_effect = none
  promotion_authority = false
```

This common type lets qualified CACE modules and the local AI act on shapes,
atoms, and molecules without special frontend-only semantics.

## Chemistry scope

The initial atom/molecule layer is intentionally conservative.

It represents:

- element label / atomic number supplied by the caller;
- 3D atom location;
- formal charge label;
- display radius;
- molecular graph membership;
- bond endpoint and bond-order label;
- geometric transforms.

It does **not** claim:

- force-field accuracy;
- bond energy;
- electronic structure;
- orbital state;
- reaction kinetics;
- thermodynamics;
- isotope correctness;
- quantum chemistry.

Those require separate qualified scientific modules later.

## Toolbox UX

Gemini should expose a **Shapes & Matter** toolbox separate from the ordinary
scientific module search while still using the same capability endpoint.

Suggested sections:

```text
Shapes 2D
  Circle
  Parabola
  Conic
  Hyperbola

Shapes 3D / N-D
  Sphere
  Hypercube

Matter
  Atom / Element
  Bond / Join

Actions
  Affine Transform
```

Dragging an item creates the corresponding CACE module node; it must not create a
frontend-only fake object.

## Atom UI

The Atom card should let the user set:

- atomic number;
- symbol;
- formal charge;
- x/y/z position;
- display radius.

Later, an element picker may populate these fields from a reviewed periodic-table
metadata source. The current core deliberately avoids silently importing a
third-party chemistry dataset.

## Molecule construction

The first production workflow is compositional:

```text
Atom ----\
          -> Bond -> Molecular geometric object -> Transform / downstream module
Atom ----/
```

A molecule may later be joined with another atom/molecule using the same typed
geometric-object contract.

## Coordinate rendering

2D objects should work in qualified 2D renderers.

3D atoms/molecules/spheres should work in qualified 3D renderers.

Higher-dimensional objects such as a 4D hypercube should use an explicit
presentation projection such as `projected.nd_3d`.

Changing renderer/view remains presentation-only.

## AI behavior

The local AI may:

- select a qualified shape or matter primitive;
- propose parameters;
- place it in an experiment proposal;
- connect only workflow-qualified edges;
- preview transforms;
- emit geometric animation events;
- build on Canvas only after approval.

The local AI may not infer unqualified physical/chemical properties from the
geometric object.

## Expansion path

Future separately qualified modules can add:

- full periodic-table metadata;
- isotope objects;
- bond-angle/dihedral tools;
- molecular-coordinate import/export;
- graph invariants;
- geometric optimization;
- molecular mechanics;
- electronic structure;
- reaction pathways;
- materials/crystal cells.

Each scientific claim must retain its own evidence level and validation contract.
