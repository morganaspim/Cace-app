from __future__ import annotations

import math

from cace_studio.core.geometry_objects import (
    GeometryObjectError,
    affine_transform_object,
    atom_object,
    bond_objects,
    hypercube_vertices,
    parse_numeric_json,
    shape_object,
)
from cace_studio.core.module import ExecutionContext, Module, ValidationError
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


def _structural_verification(name: str, obj) -> list[VerificationRecord]:
    ok = (
        isinstance(obj, dict)
        and obj.get("schema") == "cace-geometric-object-v1"
        and obj.get("evidence_authority") is False
        and obj.get("proof_effect") == "none"
        and obj.get("promotion_authority") is False
    )
    return [
        VerificationRecord(
            name,
            EvidenceKind.NUMERICAL,
            "geometric object satisfies the declared CACE object envelope",
            VerificationState.PASS if ok else VerificationState.FAIL,
            "structural envelope check only",
        )
    ]


class CircleObject(Module):
    metadata = ModuleMetadata(
        "geometry.circle",
        "Circle",
        "1.0.0",
        "Geometry",
        "Create a 2D circle as a mathematical geometric object.",
        Maturity.BETA,
        assumptions=("radius > 0",),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("center_x", "number", 0.0),
        ParameterSpec("center_y", "number", 0.0),
        ParameterSpec("radius", "number", 1.0),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["geometric object constructor; no physical semantics"],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        if float(p["radius"]) <= 0:
            raise ValidationError("circle radius must be positive")

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        cx, cy, r = float(p["center_x"]), float(p["center_y"]), float(p["radius"])
        points = [
            [cx + r * math.cos(2 * math.pi * i / 64), cy + r * math.sin(2 * math.pi * i / 64)]
            for i in range(64)
        ]
        return {
            "object": shape_object(
                "circle",
                dimension=2,
                parameters={"center": [cx, cy], "radius": r},
                representation={
                    "kind": "implicit",
                    "equation": "(x-cx)^2 + (y-cy)^2 = r^2",
                },
                points=points,
            )
        }

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("circle-object", outputs["object"])


class ParabolaObject(Module):
    metadata = ModuleMetadata(
        "geometry.parabola",
        "Parabola",
        "1.0.0",
        "Geometry",
        "Create a sampled 2D parabola y=a(x-h)^2+k.",
        Maturity.BETA,
        assumptions=("sample_span > 0", "samples >= 3"),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("a", "number", 1.0),
        ParameterSpec("h", "number", 0.0),
        ParameterSpec("k", "number", 0.0),
        ParameterSpec("sample_span", "number", 5.0),
        ParameterSpec("samples", "integer", 65),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["display samples are finite; implicit equation remains canonical"],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        if float(p["sample_span"]) <= 0 or int(p["samples"]) < 3:
            raise ValidationError("parabola requires positive span and >=3 samples")

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        a, h, k = float(p["a"]), float(p["h"]), float(p["k"])
        span, count = float(p["sample_span"]), int(p["samples"])
        xs = [h - span + (2 * span * i / (count - 1)) for i in range(count)]
        points = [[x, a * (x - h) ** 2 + k] for x in xs]
        return {
            "object": shape_object(
                "parabola",
                dimension=2,
                parameters={"a": a, "h": h, "k": k},
                representation={"kind": "explicit", "equation": "y=a(x-h)^2+k"},
                points=points,
            )
        }

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("parabola-object", outputs["object"])


class ConicObject(Module):
    metadata = ModuleMetadata(
        "geometry.conic",
        "General Conic",
        "1.0.0",
        "Geometry",
        "Create a 2D implicit conic Ax^2+Bxy+Cy^2+Dx+Ey+F=0.",
        Maturity.BETA,
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = tuple(
        ParameterSpec(name, "number", default)
        for name, default in (
            ("A", 1.0),
            ("B", 0.0),
            ("C", 1.0),
            ("D", 0.0),
            ("E", 0.0),
            ("F", -1.0),
        )
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["implicit object only; classification is not inferred by this constructor"],
    )

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        coeff = {key: float(p[key]) for key in ("A", "B", "C", "D", "E", "F")}
        return {
            "object": shape_object(
                "conic",
                dimension=2,
                parameters=coeff,
                representation={
                    "kind": "implicit",
                    "equation": "A x^2 + B x y + C y^2 + D x + E y + F = 0",
                },
            )
        }

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("conic-object", outputs["object"])


class HyperbolaObject(Module):
    metadata = ModuleMetadata(
        "geometry.hyperbola",
        "Hyperbola",
        "1.0.0",
        "Geometry",
        "Create a sampled standard-axis hyperbola ((x-h)^2/a^2)-((y-k)^2/b^2)=1.",
        Maturity.BETA,
        assumptions=("a > 0", "b > 0"),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("a", "number", 1.0),
        ParameterSpec("b", "number", 1.0),
        ParameterSpec("h", "number", 0.0),
        ParameterSpec("k", "number", 0.0),
        ParameterSpec("t_extent", "number", 2.0),
        ParameterSpec("samples", "integer", 65),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["standard-axis orientation; use affine transform for rotated views"],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        if float(p["a"]) <= 0 or float(p["b"]) <= 0:
            raise ValidationError("hyperbola a and b must be positive")
        if float(p["t_extent"]) <= 0 or int(p["samples"]) < 3:
            raise ValidationError("hyperbola requires positive t_extent and >=3 samples")

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        a, b, h, k = (float(p[name]) for name in ("a", "b", "h", "k"))
        extent, count = float(p["t_extent"]), int(p["samples"])
        ts = [-extent + (2 * extent * i / (count - 1)) for i in range(count)]
        points = []
        for t in ts:
            xoff, yoff = a * math.cosh(t), b * math.sinh(t)
            points.append([h + xoff, k + yoff])
            points.append([h - xoff, k + yoff])
        return {
            "object": shape_object(
                "hyperbola",
                dimension=2,
                parameters={"a": a, "b": b, "h": h, "k": k},
                representation={
                    "kind": "implicit",
                    "equation": "((x-h)^2/a^2)-((y-k)^2/b^2)=1",
                },
                points=points,
            )
        }

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("hyperbola-object", outputs["object"])


class SphereObject(Module):
    metadata = ModuleMetadata(
        "geometry.sphere",
        "Sphere",
        "1.0.0",
        "Geometry",
        "Create a 3D sphere as a mathematical geometric object.",
        Maturity.BETA,
        assumptions=("radius > 0",),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("center_x", "number", 0.0),
        ParameterSpec("center_y", "number", 0.0),
        ParameterSpec("center_z", "number", 0.0),
        ParameterSpec("radius", "number", 1.0),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["implicit 3D object; renderer chooses tessellation density"],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        if float(self.resolved_params(params)["radius"]) <= 0:
            raise ValidationError("sphere radius must be positive")

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        center = [float(p["center_x"]), float(p["center_y"]), float(p["center_z"])]
        radius = float(p["radius"])
        return {
            "object": shape_object(
                "sphere",
                dimension=3,
                parameters={"center": center, "radius": radius},
                representation={
                    "kind": "implicit",
                    "equation": "(x-cx)^2+(y-cy)^2+(z-cz)^2=r^2",
                },
            )
        }

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("sphere-object", outputs["object"])


class HypercubeObject(Module):
    metadata = ModuleMetadata(
        "geometry.hypercube",
        "Hypercube",
        "1.0.0",
        "Geometry",
        "Create an n-dimensional hypercube vertex object for 2<=n<=8.",
        Maturity.BETA,
        assumptions=("2 <= dimension <= 8", "half_extent > 0"),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("dimension", "integer", 4),
        ParameterSpec("half_extent", "number", 1.0),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["rendering above 3D requires a presentation projection"],
    )

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        dimension = int(p["dimension"])
        half_extent = float(p["half_extent"])
        try:
            vertices = hypercube_vertices(dimension, half_extent)
        except GeometryObjectError as exc:
            raise ValidationError(str(exc)) from exc
        return {
            "object": shape_object(
                "hypercube",
                dimension=dimension,
                parameters={"half_extent": half_extent},
                representation={
                    "kind": "vertex_set",
                    "vertex_count": len(vertices),
                },
                points=vertices,
            )
        }

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("hypercube-object", outputs["object"])


class AtomObject(Module):
    metadata = ModuleMetadata(
        "chemistry.atom",
        "Atom / Element",
        "1.0.0",
        "Chemistry Geometry",
        "Create an element-labelled atom as a 3D mathematical geometric object.",
        Maturity.BETA,
        assumptions=("atomic number and symbol are supplied consistently by the caller",),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("atomic_number", "integer", 6),
        ParameterSpec("symbol", "string", "C"),
        ParameterSpec("x", "number", 0.0),
        ParameterSpec("y", "number", 0.0),
        ParameterSpec("z", "number", 0.0),
        ParameterSpec("formal_charge", "integer", 0),
        ParameterSpec("display_radius", "number", 1.0),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "geometric/simulation atom only",
            "does not validate isotope, electron configuration, force field, or quantum state",
        ],
    )

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        try:
            obj = atom_object(
                atomic_number=int(p["atomic_number"]),
                symbol=str(p["symbol"]),
                position=[float(p["x"]), float(p["y"]), float(p["z"])],
                formal_charge=int(p["formal_charge"]),
                display_radius=float(p["display_radius"]),
            )
        except GeometryObjectError as exc:
            raise ValidationError(str(exc)) from exc
        return {"object": obj}

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("atom-object", outputs["object"])


class MolecularBondObject(Module):
    metadata = ModuleMetadata(
        "chemistry.bond",
        "Bond / Join Molecular Objects",
        "1.0.0",
        "Chemistry Geometry",
        "Join two atom/molecule geometric objects with a labelled bond edge.",
        Maturity.BETA,
    )
    inputs = (
        PortSpec("left", "geometric_object"),
        PortSpec("right", "geometric_object"),
    )
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (ParameterSpec("bond_order", "number", 1.0),)
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "bond is a graph/geometric label only",
            "no energetic, orbital, reaction, or quantum-chemical semantics",
        ],
    )

    def execute(self, inputs, params, ctx):
        try:
            obj = bond_objects(
                inputs["left"],
                inputs["right"],
                bond_order=float(self.resolved_params(params)["bond_order"]),
            )
        except GeometryObjectError as exc:
            raise ValidationError(str(exc)) from exc
        return {"object": obj}

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("molecule-object", outputs["object"])


class AffineGeometryTransform(Module):
    metadata = ModuleMetadata(
        "geometry.affine_transform_object",
        "Affine Transform Geometric Object",
        "1.0.0",
        "Geometry",
        "Apply an explicit affine transform to a CACE geometric object.",
        Maturity.BETA,
        assumptions=("matrix and translation dimensions match object dimension",),
    )
    inputs = (PortSpec("object", "geometric_object"),)
    outputs = (PortSpec("object", "geometric_object"),)
    parameters = (
        ParameterSpec("matrix_json", "string", "[[1,0],[0,1]]"),
        ParameterSpec("translation_json", "string", "[0,0]"),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.SYMBOLIC, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=["floating-point transform parameters"],
    )

    def execute(self, inputs, params, ctx):
        p = self.resolved_params(params)
        try:
            matrix = parse_numeric_json(str(p["matrix_json"]), label="matrix_json")
            translation = parse_numeric_json(
                str(p["translation_json"]),
                label="translation_json",
            )
            obj = affine_transform_object(
                inputs["object"],
                matrix=matrix,
                translation=translation,
            )
        except (GeometryObjectError, TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        return {"object": obj}

    def verify(self, inputs, params, outputs, ctx):
        return _structural_verification("affine-geometric-object", outputs["object"])


GEOMETRIC_OBJECT_MODULES = (
    CircleObject,
    ParabolaObject,
    ConicObject,
    HyperbolaObject,
    SphereObject,
    HypercubeObject,
    AtomObject,
    MolecularBondObject,
    AffineGeometryTransform,
)


def register_geometric_objects(registry):
    for cls in GEOMETRIC_OBJECT_MODULES:
        registry.register(cls)
