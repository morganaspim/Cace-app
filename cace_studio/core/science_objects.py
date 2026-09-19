from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


_PERIODIC_SYMBOLS = (
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
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
ATOMIC_NUMBERS = {symbol: index + 1 for index, symbol in enumerate(_PERIODIC_SYMBOLS)}

# Compact, auditable descriptor table for the initial materials-search demo.
# Values are ordinary reference descriptors, not a learned property model.
DEMO_ELEMENT_DESCRIPTORS: dict[str, dict[str, float]] = {
    "H": {"mass_u": 1.008, "en": 2.20, "radius_pm": 31.0, "valence": 1.0},
    "B": {"mass_u": 10.81, "en": 2.04, "radius_pm": 85.0, "valence": 3.0},
    "C": {"mass_u": 12.011, "en": 2.55, "radius_pm": 76.0, "valence": 4.0},
    "N": {"mass_u": 14.007, "en": 3.04, "radius_pm": 71.0, "valence": 5.0},
    "O": {"mass_u": 15.999, "en": 3.44, "radius_pm": 66.0, "valence": 6.0},
    "F": {"mass_u": 18.998, "en": 3.98, "radius_pm": 57.0, "valence": 7.0},
    "Na": {"mass_u": 22.990, "en": 0.93, "radius_pm": 166.0, "valence": 1.0},
    "Mg": {"mass_u": 24.305, "en": 1.31, "radius_pm": 141.0, "valence": 2.0},
    "Al": {"mass_u": 26.982, "en": 1.61, "radius_pm": 121.0, "valence": 3.0},
    "Si": {"mass_u": 28.085, "en": 1.90, "radius_pm": 111.0, "valence": 4.0},
    "P": {"mass_u": 30.974, "en": 2.19, "radius_pm": 107.0, "valence": 5.0},
    "S": {"mass_u": 32.06, "en": 2.58, "radius_pm": 105.0, "valence": 6.0},
    "Cl": {"mass_u": 35.45, "en": 3.16, "radius_pm": 102.0, "valence": 7.0},
    "K": {"mass_u": 39.098, "en": 0.82, "radius_pm": 203.0, "valence": 1.0},
    "Ca": {"mass_u": 40.078, "en": 1.00, "radius_pm": 176.0, "valence": 2.0},
    "Ti": {"mass_u": 47.867, "en": 1.54, "radius_pm": 160.0, "valence": 4.0},
    "Fe": {"mass_u": 55.845, "en": 1.83, "radius_pm": 132.0, "valence": 8.0},
    "Ni": {"mass_u": 58.693, "en": 1.91, "radius_pm": 124.0, "valence": 10.0},
    "Cu": {"mass_u": 63.546, "en": 1.90, "radius_pm": 132.0, "valence": 11.0},
    "Zn": {"mass_u": 65.38, "en": 1.65, "radius_pm": 122.0, "valence": 12.0},
}


def _vec3(value: Sequence[float]) -> tuple[float, float, float]:
    if len(value) != 3:
        raise ValueError("3D position must contain exactly three coordinates")
    return (float(value[0]), float(value[1]), float(value[2]))


@dataclass(frozen=True)
class ThirdPartyAssetMetadata:
    source: str
    license_id: str = "unspecified"
    attribution: str = ""
    content_sha256: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "license_id": self.license_id,
            "attribution": self.attribution,
            "content_sha256": self.content_sha256,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class Atom:
    symbol: str
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    formal_charge: int = 0
    isotope: int | None = None

    def __post_init__(self) -> None:
        if self.symbol not in ATOMIC_NUMBERS:
            raise ValueError(f"unknown element symbol: {self.symbol!r}")
        object.__setattr__(self, "position", _vec3(self.position))
        if self.isotope is not None and int(self.isotope) <= 0:
            raise ValueError("isotope mass number must be positive")

    @property
    def atomic_number(self) -> int:
        return ATOMIC_NUMBERS[self.symbol]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "atomic_number": self.atomic_number,
            "position": list(self.position),
            "formal_charge": int(self.formal_charge),
            "isotope": self.isotope,
        }


@dataclass(frozen=True)
class Bond:
    atom_a: int
    atom_b: int
    order: float = 1.0
    kind: str = "covalent"

    def __post_init__(self) -> None:
        if self.atom_a < 0 or self.atom_b < 0 or self.atom_a == self.atom_b:
            raise ValueError("bond endpoints must be distinct non-negative indices")
        if float(self.order) <= 0.0:
            raise ValueError("bond order must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_a": int(self.atom_a),
            "atom_b": int(self.atom_b),
            "order": float(self.order),
            "kind": self.kind,
        }


@dataclass(frozen=True)
class Molecule:
    atoms: tuple[Atom, ...]
    bonds: tuple[Bond, ...] = ()
    name: str = ""
    total_formal_charge: int | None = None
    provenance: ThirdPartyAssetMetadata | None = None

    def __post_init__(self) -> None:
        if not self.atoms:
            raise ValueError("molecule must contain at least one atom")
        for bond in self.bonds:
            if max(bond.atom_a, bond.atom_b) >= len(self.atoms):
                raise ValueError("bond endpoint lies outside molecule atom list")
        if self.total_formal_charge is None:
            object.__setattr__(
                self,
                "total_formal_charge",
                sum(atom.formal_charge for atom in self.atoms),
            )

    @property
    def formula(self) -> str:
        counts = Counter(atom.symbol for atom in self.atoms)
        symbols = sorted(counts)
        if "C" in counts:
            symbols = ["C"] + (["H"] if "H" in counts else []) + [
                symbol for symbol in symbols if symbol not in {"C", "H"}
            ]
        return "".join(
            symbol + (str(counts[symbol]) if counts[symbol] != 1 else "")
            for symbol in symbols
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "formula": self.formula,
            "total_formal_charge": int(self.total_formal_charge or 0),
            "atoms": [atom.to_dict() for atom in self.atoms],
            "bonds": [bond.to_dict() for bond in self.bonds],
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


_ALLOWED_RESIDUES = frozenset("ACDEFGHIKLMNPQRSTVWYBXZUOJ")


@dataclass(frozen=True)
class ProteinSequence:
    sequence: str
    name: str = ""
    provenance: ThirdPartyAssetMetadata | None = None

    def __post_init__(self) -> None:
        normalized = "".join(str(self.sequence).split()).upper()
        if not normalized:
            raise ValueError("protein sequence must not be empty")
        invalid = sorted(set(normalized) - _ALLOWED_RESIDUES)
        if invalid:
            raise ValueError(f"protein sequence contains unsupported residues: {invalid}")
        object.__setattr__(self, "sequence", normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "name": self.name,
            "length": len(self.sequence),
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


@dataclass(frozen=True)
class ProteinStructure:
    sequence: ProteinSequence
    ca_coordinates: tuple[tuple[float, float, float], ...]
    plddt: tuple[float, ...] = ()
    chain_ids: tuple[str, ...] = ()
    provenance: ThirdPartyAssetMetadata | None = None
    method: str = "unspecified"
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        coords = tuple(_vec3(point) for point in self.ca_coordinates)
        object.__setattr__(self, "ca_coordinates", coords)
        if len(coords) != len(self.sequence.sequence):
            raise ValueError("protein coordinate count must equal sequence length")
        if self.plddt and len(self.plddt) != len(coords):
            raise ValueError("pLDDT/confidence length must equal coordinate count")
        if self.chain_ids and len(self.chain_ids) != len(coords):
            raise ValueError("chain_ids length must equal coordinate count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence.to_dict(),
            "ca_coordinates": [list(point) for point in self.ca_coordinates],
            "plddt": list(self.plddt),
            "chain_ids": list(self.chain_ids),
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "method": self.method,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class MaterialCandidate:
    formula: str
    composition: tuple[tuple[str, int], ...]
    descriptors: Mapping[str, float]
    score: float
    target: str
    evidence_class: str = "heuristic-screening"
    uncertainty_note: str = (
        "Descriptor score only; not a measured property, synthesis guarantee, or discovery claim."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula": self.formula,
            "composition": {symbol: count for symbol, count in self.composition},
            "descriptors": {str(k): float(v) for k, v in self.descriptors.items()},
            "score": float(self.score),
            "target": self.target,
            "evidence_class": self.evidence_class,
            "uncertainty_note": self.uncertainty_note,
            "synthesis_instructions": False,
        }


@dataclass(frozen=True)
class PhysicsCanvasObject:
    object_id: str
    display_name: str
    family: str
    established: bool
    properties: Mapping[str, Any] = field(default_factory=dict)
    caveats: tuple[str, ...] = ()

    @property
    def evidence_label(self) -> str:
        return "established-physics-entity" if self.established else "theoretical-research-visualization"

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "display_name": self.display_name,
            "family": self.family,
            "established": self.established,
            "evidence_label": self.evidence_label,
            "properties": dict(self.properties),
            "caveats": list(self.caveats),
        }


def content_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def molecule_from_mapping(payload: Mapping[str, Any]) -> Molecule:
    atoms = tuple(
        Atom(
            symbol=str(item["symbol"]),
            position=tuple(item.get("position", (0.0, 0.0, 0.0))),
            formal_charge=int(item.get("formal_charge", 0)),
            isotope=(int(item["isotope"]) if item.get("isotope") is not None else None),
        )
        for item in payload.get("atoms", ())
    )
    bonds = tuple(
        Bond(
            int(item["atom_a"]),
            int(item["atom_b"]),
            float(item.get("order", 1.0)),
            str(item.get("kind", "covalent")),
        )
        for item in payload.get("bonds", ())
    )
    return Molecule(
        atoms=atoms,
        bonds=bonds,
        name=str(payload.get("name", "")),
        total_formal_charge=(
            int(payload["total_formal_charge"])
            if payload.get("total_formal_charge") is not None
            else None
        ),
    )


def molecule_from_json(text: str) -> Molecule:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("molecule JSON must contain an object")
    return molecule_from_mapping(payload)
