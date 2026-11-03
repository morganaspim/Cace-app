from __future__ import annotations

from copy import deepcopy
import itertools
import json
import math
import re
from typing import Any, Iterable, Mapping, Sequence



ELEMENT_SYMBOLS = (
    "", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)

_ELEMENT_SYMBOL = re.compile(r"^[A-Z][a-z]?$")


class GeometryObjectError(ValueError):
    pass


def _finite(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise GeometryObjectError(f"{label} must be finite")
    return number


def shape_object(
    kind: str,
    *,
    dimension: int,
    parameters: Mapping[str, Any],
    representation: Mapping[str, Any],
    points: Sequence[Sequence[float]] = (),
) -> dict[str, Any]:
    if not kind:
        raise GeometryObjectError("shape kind must be non-empty")
    if dimension < 2:
        raise GeometryObjectError("shape dimension must be >= 2")
    canonical_points = [
        [_finite(value, "point coordinate") for value in point]
        for point in points
    ]
    if any(len(point) != dimension for point in canonical_points):
        raise GeometryObjectError("point dimension mismatch")
    return {
        "schema": "cace-geometric-object-v1",
        "object_type": "shape",
        "geometry_kind": kind,
        "dimension": int(dimension),
        "parameters": deepcopy(dict(parameters)),
        "representation": deepcopy(dict(representation)),
        "points": canonical_points,
        "transforms": [],
        "evidence_authority": False,
        "proof_effect": "none",
        "promotion_authority": False,
    }


def atom_object(
    *,
    atomic_number: int,
    symbol: str,
    position: Sequence[float],
    formal_charge: int = 0,
    display_radius: float = 1.0,
) -> dict[str, Any]:
    atomic_number = int(atomic_number)
    if not 1 <= atomic_number <= 118:
        raise GeometryObjectError("atomic_number must be between 1 and 118")
    if not isinstance(symbol, str) or not _ELEMENT_SYMBOL.fullmatch(symbol):
        raise GeometryObjectError("symbol must be a canonical element symbol")
    if symbol != ELEMENT_SYMBOLS[atomic_number]:
        raise GeometryObjectError(
            f"atomic number {atomic_number} requires symbol {ELEMENT_SYMBOLS[atomic_number]}"
        )
    if len(position) != 3:
        raise GeometryObjectError("atom position must be 3D")
    radius = _finite(display_radius, "display_radius")
    if radius <= 0:
        raise GeometryObjectError("display_radius must be positive")
    return {
        "schema": "cace-geometric-object-v1",
        "object_type": "atom",
        "geometry_kind": "atom",
        "dimension": 3,
        "atomic_number": atomic_number,
        "symbol": symbol,
        "formal_charge": int(formal_charge),
        "display_radius": radius,
        "position": [_finite(value, "position") for value in position],
        "points": [[_finite(value, "position") for value in position]],
        "transforms": [],
        "evidence_authority": False,
        "proof_effect": "none",
        "promotion_authority": False,
    }


def _atoms_and_bonds(obj: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    object_type = obj.get("object_type")
    if object_type == "atom":
        atom = {
            "atomic_number": int(obj["atomic_number"]),
            "symbol": str(obj["symbol"]),
            "formal_charge": int(obj.get("formal_charge", 0)),
            "display_radius": float(obj.get("display_radius", 1.0)),
            "position": [float(value) for value in obj["position"]],
        }
        return [atom], []
    if object_type == "molecule":
        atoms = deepcopy(list(obj.get("atoms", [])))
        bonds = deepcopy(list(obj.get("bonds", [])))
        return atoms, bonds
    raise GeometryObjectError("bonding accepts only atom or molecule objects")


def bond_objects(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    bond_order: float = 1.0,
) -> dict[str, Any]:
    order = _finite(bond_order, "bond_order")
    if order <= 0:
        raise GeometryObjectError("bond_order must be positive")
    left_atoms, left_bonds = _atoms_and_bonds(left)
    right_atoms, right_bonds = _atoms_and_bonds(right)

    atoms = left_atoms + right_atoms
    offset = len(left_atoms)
    bonds = list(left_bonds)
    bonds.extend(
        {
            **bond,
            "a": int(bond["a"]) + offset,
            "b": int(bond["b"]) + offset,
        }
        for bond in right_bonds
    )
    bonds.append({"a": len(left_atoms) - 1, "b": offset, "order": order})

    return {
        "schema": "cace-geometric-object-v1",
        "object_type": "molecule",
        "geometry_kind": "molecular_graph",
        "dimension": 3,
        "atoms": atoms,
        "bonds": bonds,
        "points": [list(atom["position"]) for atom in atoms],
        "transforms": [],
        "model_scope": (
            "geometric molecular graph only; no force field, electronic-structure, "
            "bond-energy, reaction, or quantum-chemistry claim"
        ),
        "evidence_authority": False,
        "proof_effect": "none",
        "promotion_authority": False,
    }


def hypercube_vertices(dimension: int, half_extent: float) -> list[list[float]]:
    dimension = int(dimension)
    if not 2 <= dimension <= 8:
        raise GeometryObjectError("hypercube dimension must be between 2 and 8")
    extent = _finite(half_extent, "half_extent")
    if extent <= 0:
        raise GeometryObjectError("half_extent must be positive")
    return [
        [extent * sign for sign in signs]
        for signs in itertools.product((-1.0, 1.0), repeat=dimension)
    ]


def affine_transform_object(
    obj: Mapping[str, Any],
    *,
    matrix: Sequence[Sequence[float]],
    translation: Sequence[float],
) -> dict[str, Any]:
    if obj.get("schema") != "cace-geometric-object-v1":
        raise GeometryObjectError("unsupported geometric object schema")
    dimension = int(obj.get("dimension", 0))
    if dimension <= 0:
        raise GeometryObjectError("geometric object dimension is invalid")
    if len(matrix) != dimension or any(len(row) != dimension for row in matrix):
        raise GeometryObjectError("affine matrix must be square with object dimension")
    if len(translation) != dimension:
        raise GeometryObjectError("translation dimension mismatch")

    m = [[_finite(value, "matrix") for value in row] for row in matrix]
    t = [_finite(value, "translation") for value in translation]

    def transform_point(point: Sequence[float]) -> list[float]:
        if len(point) != dimension:
            raise GeometryObjectError("stored point dimension mismatch")
        return [
            sum(m[row][col] * float(point[col]) for col in range(dimension)) + t[row]
            for row in range(dimension)
        ]

    out = deepcopy(dict(obj))
    points = [transform_point(point) for point in obj.get("points", [])]
    out["points"] = points
    if out.get("object_type") == "atom":
        out["position"] = list(points[0])
    elif out.get("object_type") == "molecule":
        atoms = deepcopy(list(out.get("atoms", [])))
        for index, atom in enumerate(atoms):
            atom["position"] = list(points[index])
        out["atoms"] = atoms

    transforms = list(out.get("transforms", []))
    transforms.append(
        {
            "kind": "affine",
            "matrix": m,
            "translation": t,
        }
    )
    out["transforms"] = transforms
    if out.get("object_type") == "shape":
        out["geometry_kind"] = "affine_transform(" + str(obj.get("geometry_kind")) + ")"
    return out


def parse_numeric_json(text: str, *, label: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeometryObjectError(f"{label} must be valid JSON") from exc
