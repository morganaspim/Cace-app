from __future__ import annotations

from itertools import combinations, product
import json
import math
from typing import Any, Mapping

import numpy as np

from cace_studio.core.module import Module, ExecutionContext, ValidationError
from cace_studio.core.science_objects import (
    Atom,
    DEMO_ELEMENT_DESCRIPTORS,
    MaterialCandidate,
    PhysicsCanvasObject,
    ProteinSequence,
    ProteinStructure,
    ThirdPartyAssetMetadata,
    content_sha256,
    molecule_from_json,
)
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ParameterSpec,
    PortSpec,
    ProofStatus,
)
from cace_studio.core.verification import VerificationRecord, VerificationState


_RESIDUE_3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "SEC": "U", "PYL": "O", "ASX": "B", "GLX": "Z", "UNK": "X",
    "MSE": "M",
}
_HYDROPHOBIC = frozenset("AVILMFWYC")


def parse_pdb_ca_structure(
    pdb_text: str,
    *,
    source: str = "user-supplied-pdb",
    license_id: str = "user-supplied",
    attribution: str = "",
) -> ProteinStructure:
    """Parse one C-alpha coordinate per residue from PDB ATOM/HETATM records.

    The importer is intentionally small and auditable. It does not infer bonds,
    secondary structure, biological assemblies, or missing residues.
    """
    residues: list[tuple[str, str, str, tuple[float, float, float], float | None]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in str(pdb_text).splitlines():
        if not (raw.startswith("ATOM  ") or raw.startswith("HETATM")):
            continue
        if len(raw) < 54:
            continue
        atom_name = raw[12:16].strip()
        if atom_name != "CA":
            continue
        resname = raw[17:20].strip().upper()
        chain = raw[21:22].strip() or "_"
        resseq = raw[22:26].strip()
        icode = raw[26:27].strip()
        key = (chain, resseq, icode)
        if key in seen:
            continue
        try:
            x = float(raw[30:38])
            y = float(raw[38:46])
            z = float(raw[46:54])
        except ValueError:
            continue
        bfactor = None
        if len(raw) >= 66:
            try:
                bfactor = float(raw[60:66])
            except ValueError:
                bfactor = None
        residues.append((resname, chain, resseq, (x, y, z), bfactor))
        seen.add(key)

    if not residues:
        raise ValueError("PDB text contained no parseable C-alpha residues")

    sequence_text = "".join(_RESIDUE_3_TO_1.get(item[0], "X") for item in residues)
    provenance = ThirdPartyAssetMetadata(
        source=str(source),
        license_id=str(license_id),
        attribution=str(attribution),
        content_sha256=content_sha256(pdb_text),
        notes=(
            "Imported coordinates are a prediction/model unless independently established otherwise.",
        ),
    )
    sequence = ProteinSequence(sequence_text, provenance=provenance)
    plddt = (
        tuple(float(item[4]) for item in residues)
        if all(item[4] is not None for item in residues)
        else ()
    )
    return ProteinStructure(
        sequence=sequence,
        ca_coordinates=tuple(item[3] for item in residues),
        plddt=plddt,
        chain_ids=tuple(item[1] for item in residues),
        provenance=provenance,
        method="pdb-ca-import",
        limitations=(
            "Only C-alpha coordinates are imported.",
            "Missing residues/atoms and biological assembly semantics are not reconstructed.",
        ),
    )


def initial_ca_helix(length: int) -> np.ndarray:
    """Low-cost initial chain with approximately 3.8 Å adjacent spacing."""
    if length < 1:
        raise ValueError("length must be positive")
    indices = np.arange(length, dtype=float)
    theta = np.deg2rad(100.0) * indices
    radius = 2.3
    rise = 1.5
    return np.column_stack((radius * np.cos(theta), radius * np.sin(theta), rise * indices))


def coarse_protein_energy(sequence: str, coordinates: np.ndarray) -> float:
    """Inspectably simple C-alpha energy proxy for demonstration/search.

    Terms: adjacent-distance penalty, nonbonded steric repulsion, weak
    hydrophobic-contact attraction, and a tiny compactness regularizer.
    This is not a force field or thermodynamic free-energy calculation.
    """
    seq = str(sequence).upper()
    xyz = np.asarray(coordinates, dtype=float)
    if xyz.shape != (len(seq), 3):
        raise ValueError("coordinates must have shape (sequence length, 3)")
    if not np.all(np.isfinite(xyz)):
        raise ValueError("coordinates must be finite")
    if len(seq) == 1:
        return 0.0

    adjacent = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    bond_term = 12.0 * float(np.sum((adjacent - 3.8) ** 2))

    diff = xyz[:, None, :] - xyz[None, :, :]
    distance = np.linalg.norm(diff, axis=2)
    i, j = np.triu_indices(len(seq), k=3)
    dij = np.maximum(distance[i, j], 0.5)

    clash_ratio = np.maximum(0.0, 3.4 / dij - 1.0)
    clash_term = 30.0 * float(np.sum(clash_ratio**4))

    hydro = np.array([residue in _HYDROPHOBIC for residue in seq], dtype=bool)
    hydro_pairs = hydro[i] & hydro[j]
    contact_shape = np.exp(-0.5 * ((dij - 6.0) / 1.5) ** 2)
    hydro_term = -0.6 * float(np.sum(contact_shape[hydro_pairs]))

    centered = xyz - xyz.mean(axis=0, keepdims=True)
    radius_gyration_sq = float(np.mean(np.sum(centered * centered, axis=1)))
    compactness_term = 0.002 * radius_gyration_sq
    return bond_term + clash_term + hydro_term + compactness_term


def _random_pivot_move(
    coordinates: np.ndarray,
    rng: np.random.Generator,
    max_angle: float,
) -> np.ndarray:
    xyz = np.asarray(coordinates, dtype=float)
    if len(xyz) < 3:
        return xyz.copy()
    pivot = int(rng.integers(0, len(xyz) - 1))
    axis = rng.normal(size=3)
    norm = float(np.linalg.norm(axis))
    if norm == 0.0:
        axis = np.array([1.0, 0.0, 0.0])
    else:
        axis /= norm
    angle = float(rng.uniform(-max_angle, max_angle))
    c = math.cos(angle)
    s = math.sin(angle)
    kx, ky, kz = axis
    rotation = np.array(
        [
            [c + kx * kx * (1 - c), kx * ky * (1 - c) - kz * s, kx * kz * (1 - c) + ky * s],
            [ky * kx * (1 - c) + kz * s, c + ky * ky * (1 - c), ky * kz * (1 - c) - kx * s],
            [kz * kx * (1 - c) - ky * s, kz * ky * (1 - c) + kx * s, c + kz * kz * (1 - c)],
        ],
        dtype=float,
    )
    result = xyz.copy()
    origin = xyz[pivot].copy()
    suffix = xyz[pivot + 1 :] - origin
    result[pivot + 1 :] = suffix @ rotation.T + origin
    return result


def search_coarse_fold(
    sequence: str,
    *,
    seed: int,
    steps: int = 1200,
    initial_coordinates: np.ndarray | None = None,
    start_temperature: float = 1.5,
    end_temperature: float = 0.03,
    max_angle: float = 0.7,
) -> tuple[np.ndarray, float, np.ndarray]:
    seq = str(sequence).upper()
    if not seq:
        raise ValueError("sequence must not be empty")
    if not 1 <= int(steps) <= 50_000:
        raise ValueError("steps must be in 1..50000")
    if start_temperature <= 0.0 or end_temperature <= 0.0:
        raise ValueError("temperatures must be positive")
    if max_angle <= 0.0 or not math.isfinite(max_angle):
        raise ValueError("max_angle must be finite and positive")

    current = (
        initial_ca_helix(len(seq))
        if initial_coordinates is None
        else np.asarray(initial_coordinates, dtype=float).copy()
    )
    if current.shape != (len(seq), 3):
        raise ValueError("initial coordinates must match sequence length")
    rng = np.random.default_rng(int(seed))
    current_energy = coarse_protein_energy(seq, current)
    best = current.copy()
    best_energy = current_energy
    trace = np.empty(int(steps) + 1, dtype=float)
    trace[0] = best_energy

    if steps == 1:
        temperatures = np.array([start_temperature], dtype=float)
    else:
        temperatures = np.geomspace(start_temperature, end_temperature, num=int(steps))

    for index, temperature in enumerate(temperatures, start=1):
        proposal = _random_pivot_move(current, rng, max_angle)
        proposal_energy = coarse_protein_energy(seq, proposal)
        delta = proposal_energy - current_energy
        accept = delta <= 0.0 or rng.random() < math.exp(-delta / float(temperature))
        if accept:
            current = proposal
            current_energy = proposal_energy
        if current_energy < best_energy:
            best = current.copy()
            best_energy = current_energy
        trace[index] = best_energy
    return best, float(best_energy), trace


SAFE_HOME_EXPERIMENTS: dict[str, dict[str, Any]] = {
    "red_cabbage_indicator": {
        "title": "Household pH indicator observations",
        "risk_level": "low",
        "materials": [
            "pre-prepared red-cabbage indicator or commercial food-safe pH indicator",
            "small open cups",
            "water",
            "small household food-safe samples such as lemon juice or baking-soda solution",
        ],
        "procedure": [
            "Place small samples in separate open cups.",
            "Add a small amount of indicator to each cup.",
            "Record the observed color without tasting the mixtures.",
        ],
        "prohibited_substitutions": [
            "cleaners", "bleach", "ammonia", "unknown chemicals", "sealed containers"
        ],
        "observable": "indicator color",
        "disposal": "Use only food-safe household samples; dilute with water and dispose according to local household guidance.",
    },
    "salt_crystal_evaporation": {
        "title": "Room-temperature salt crystallization",
        "risk_level": "low",
        "materials": ["table salt", "water", "open shallow dish", "measuring spoon"],
        "procedure": [
            "Dissolve table salt in water at room temperature.",
            "Leave the open dish in a stable location away from children and pets.",
            "Record crystal appearance as water evaporates naturally.",
        ],
        "prohibited_substitutions": ["unknown salts", "heating", "sealed vessels"],
        "observable": "crystal growth over time",
        "disposal": "Small amounts of table-salt solution may be disposed of as ordinary household material where locally permitted.",
    },
    "food_color_chromatography": {
        "title": "Water-based color chromatography",
        "risk_level": "low",
        "materials": ["coffee filter or chromatography paper", "water", "food coloring or washable marker", "small cup"],
        "procedure": [
            "Place a small color spot near one end of the paper.",
            "Touch only the paper edge below the spot to a shallow amount of water.",
            "Observe and record the separated color bands as water moves through the paper.",
        ],
        "prohibited_substitutions": ["organic solvents", "unknown inks", "flammable liquids"],
        "observable": "relative color-band travel distances",
        "disposal": "Dispose of paper and water as ordinary household waste where locally permitted.",
    },
}


def safe_home_experiment(experiment_id: str) -> dict[str, Any]:
    try:
        template = SAFE_HOME_EXPERIMENTS[str(experiment_id)]
    except KeyError as exc:
        raise ValueError(
            "experiment is not in the Safe Home Lab whitelist; use simulation-only mode"
        ) from exc
    return {
        "experiment_id": str(experiment_id),
        **json.loads(json.dumps(template)),
        "safety_boundary": (
            "Low-risk whitelist only. Do not substitute unknown chemicals or scale into hazardous conditions."
        ),
    }


def _candidate_formula(composition: tuple[tuple[str, int], ...]) -> str:
    return "".join(symbol + (str(count) if count != 1 else "") for symbol, count in composition)


def material_descriptors(composition: tuple[tuple[str, int], ...]) -> dict[str, float]:
    total = sum(count for _, count in composition)
    if total <= 0:
        raise ValueError("composition must contain positive stoichiometric counts")
    rows = []
    weights = []
    for symbol, count in composition:
        if symbol not in DEMO_ELEMENT_DESCRIPTORS:
            raise ValueError(f"no built-in demo descriptors for element {symbol}")
        if int(count) <= 0:
            raise ValueError("stoichiometric counts must be positive")
        rows.append(DEMO_ELEMENT_DESCRIPTORS[symbol])
        weights.append(int(count))
    fractions = np.asarray(weights, dtype=float) / total
    masses = np.asarray([row["mass_u"] for row in rows], dtype=float)
    ens = np.asarray([row["en"] for row in rows], dtype=float)
    radii = np.asarray([row["radius_pm"] for row in rows], dtype=float)
    valence = np.asarray([row["valence"] for row in rows], dtype=float)
    entropy = -float(np.sum(fractions * np.log(np.maximum(fractions, 1e-15))))
    return {
        "mean_atomic_mass_u": float(np.sum(fractions * masses)),
        "electronegativity_span": float(np.max(ens) - np.min(ens)),
        "radius_mismatch_fraction": float((np.max(radii) - np.min(radii)) / max(np.mean(radii), 1e-12)),
        "mean_valence_descriptor": float(np.sum(fractions * valence)),
        "composition_entropy": entropy,
    }


def score_material(descriptors: Mapping[str, float], target: str) -> float:
    mass = float(descriptors["mean_atomic_mass_u"])
    en_span = float(descriptors["electronegativity_span"])
    radius_mismatch = float(descriptors["radius_mismatch_fraction"])
    entropy = float(descriptors["composition_entropy"])
    if target == "lightweight":
        return 1.0 / (1.0 + mass / 20.0) + 0.05 * entropy
    if target == "ionic_contrast":
        return en_span - 0.25 * radius_mismatch
    if target == "balanced":
        return 0.45 * en_span + 0.35 / (1.0 + mass / 40.0) + 0.2 * entropy - 0.15 * radius_mismatch
    raise ValueError(f"unknown materials target: {target}")


def search_material_candidates(
    elements: tuple[str, ...],
    *,
    target: str,
    max_stoich: int = 3,
    limit: int = 12,
) -> tuple[MaterialCandidate, ...]:
    unique = tuple(dict.fromkeys(elements))
    if not 2 <= len(unique) <= 8:
        raise ValueError("materials search requires 2..8 distinct elements")
    if any(symbol not in DEMO_ELEMENT_DESCRIPTORS for symbol in unique):
        missing = sorted(symbol for symbol in unique if symbol not in DEMO_ELEMENT_DESCRIPTORS)
        raise ValueError(f"unsupported demo descriptor elements: {missing}")
    if not 1 <= int(max_stoich) <= 4:
        raise ValueError("max_stoich must be in 1..4")
    candidates: list[MaterialCandidate] = []
    seen_compositions: set[tuple[tuple[str, int], ...]] = set()
    for pair in combinations(unique, 2):
        for counts in product(range(1, int(max_stoich) + 1), repeat=2):
            divisor = math.gcd(int(counts[0]), int(counts[1]))
            reduced = tuple(int(count) // divisor for count in counts)
            composition = tuple((symbol, count) for symbol, count in zip(pair, reduced))
            if composition in seen_compositions:
                continue
            seen_compositions.add(composition)
            descriptors = material_descriptors(composition)
            score = score_material(descriptors, target)
            candidates.append(
                MaterialCandidate(
                    formula=_candidate_formula(composition),
                    composition=composition,
                    descriptors=descriptors,
                    score=score,
                    target=target,
                )
            )
    candidates.sort(key=lambda item: (-item.score, item.formula))
    return tuple(candidates[: max(1, int(limit))])


_PHYSICS_OBJECTS: dict[str, PhysicsCanvasObject] = {}


def _register_particle(
    object_id: str,
    display_name: str,
    family: str,
    *,
    charge_e: float | str,
    spin: str,
    caveats: tuple[str, ...] = (),
) -> None:
    _PHYSICS_OBJECTS[object_id] = PhysicsCanvasObject(
        object_id=object_id,
        display_name=display_name,
        family=family,
        established=True,
        properties={"electric_charge_e": charge_e, "spin": spin},
        caveats=caveats,
    )


for _qid, _name, _charge in (
    ("up_quark", "Up quark", 2 / 3),
    ("down_quark", "Down quark", -1 / 3),
    ("strange_quark", "Strange quark", -1 / 3),
    ("charm_quark", "Charm quark", 2 / 3),
    ("top_quark", "Top quark", 2 / 3),
    ("bottom_quark", "Bottom quark", -1 / 3),
):
    _register_particle(
        _qid,
        _name,
        "quark",
        charge_e=_charge,
        spin="1/2",
        caveats=("Quarks are confined; this canvas object does not represent an isolated free quark state.",),
    )

_register_particle("electron", "Electron", "lepton", charge_e=-1.0, spin="1/2")
_register_particle("photon", "Photon", "gauge-boson", charge_e=0.0, spin="1")
_register_particle("gluon", "Gluon", "gauge-boson", charge_e=0.0, spin="1")
_register_particle("w_boson", "W boson", "gauge-boson", charge_e="±1", spin="1")
_register_particle("z_boson", "Z boson", "gauge-boson", charge_e=0.0, spin="1")
_register_particle("higgs", "Higgs boson", "scalar-boson", charge_e=0.0, spin="0")

for _oid, _name, _family in (
    ("string_segment", "String segment", "string-theory"),
    ("worldsheet", "Worldsheet", "string-theory"),
    ("brane", "Brane-like object", "string-theory"),
    ("generic_field", "Generic field", "field-theory"),
):
    _PHYSICS_OBJECTS[_oid] = PhysicsCanvasObject(
        object_id=_oid,
        display_name=_name,
        family=_family,
        established=False,
        properties={},
        caveats=("Theoretical/research visualization; not an experimentally established particle object.",),
    )


def physics_canvas_object(object_id: str) -> PhysicsCanvasObject:
    try:
        return _PHYSICS_OBJECTS[str(object_id)]
    except KeyError as exc:
        raise ValueError(f"unknown physics canvas object: {object_id}") from exc


class AtomObjectModule(Module):
    metadata = ModuleMetadata(
        "chemistry.atom_object",
        "Atom Object",
        "0.1.0",
        "Chemistry",
        "Create a typed atom with element identity, charge, and 3D position.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("atom", "atom_object"),)
    parameters = (
        ParameterSpec("symbol", "string", "C"),
        ParameterSpec("formal_charge", "integer", 0),
        ParameterSpec("x", "number", 0.0),
        ParameterSpec("y", "number", 0.0),
        ParameterSpec("z", "number", 0.0),
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        try:
            Atom(
                str(p["symbol"]),
                (float(p["x"]), float(p["y"]), float(p["z"])),
                int(p["formal_charge"]),
            )
        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        return {
            "atom": Atom(
                str(params["symbol"]),
                (float(params["x"]), float(params["y"]), float(params["z"])),
                int(params["formal_charge"]),
            )
        }


class MoleculeJSONModule(Module):
    metadata = ModuleMetadata(
        "chemistry.molecule_json",
        "Molecule from JSON",
        "0.1.0",
        "Chemistry",
        "Build a typed molecule from explicit atoms and bonds.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("molecule", "molecule_object"),)
    parameters = (
        ParameterSpec(
            "molecule_json",
            "string",
            '{"name":"water","atoms":[{"symbol":"O"},{"symbol":"H"},{"symbol":"H"}],"bonds":[{"atom_a":0,"atom_b":1},{"atom_a":0,"atom_b":2}]}',
        ),
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        try:
            molecule_from_json(str(self.resolved_params(params)["molecule_json"]))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        return {"molecule": molecule_from_json(str(params["molecule_json"]))}


class ProteinSequenceModule(Module):
    metadata = ModuleMetadata(
        "protein.sequence",
        "Protein Sequence",
        "0.1.0",
        "Protein Science",
        "Create a typed protein sequence for folding/prediction modules.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("sequence", "protein_sequence"),)
    parameters = (
        ParameterSpec("sequence", "string", "ACDEFGHIKLMNPQRSTVWY"),
        ParameterSpec("name", "string", ""),
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        try:
            ProteinSequence(str(p["sequence"]), name=str(p["name"]))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        return {
            "sequence": ProteinSequence(
                str(params["sequence"]),
                name=str(params["name"]),
            )
        }


class AlphaFoldPDBImportModule(Module):
    metadata = ModuleMetadata(
        "protein.alphafold_pdb_import",
        "AlphaFold-Compatible PDB Import",
        "0.1.0",
        "Protein Science",
        "Import C-alpha coordinates and confidence fields from user-supplied PDB text while preserving attribution metadata.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "PDB input is supplied by the user/import workflow.",
            "The module does not download or bundle AlphaFold model weights.",
        ),
    )
    inputs = (PortSpec("pdb_text", "string"),)
    outputs = (
        PortSpec("sequence", "protein_sequence"),
        PortSpec("structure", "protein_structure"),
    )
    parameters = (
        ParameterSpec("source", "string", "user-supplied-pdb"),
        ParameterSpec("license_id", "string", "user-supplied"),
        ParameterSpec("attribution", "string", ""),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL},
        unit_tests=True,
        documentation=True,
        limitations=[
            "C-alpha-only importer; not a complete structural-biology parser.",
            "Imported prediction confidence is not experimental validation.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        try:
            parse_pdb_ca_structure(
                str(inputs["pdb_text"]),
                source=str(p["source"]),
                license_id=str(p["license_id"]),
                attribution=str(p["attribution"]),
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        structure = parse_pdb_ca_structure(
            str(inputs["pdb_text"]),
            source=str(params["source"]),
            license_id=str(params["license_id"]),
            attribution=str(params["attribution"]),
        )
        return {"sequence": structure.sequence, "structure": structure}

    def verify(self, inputs, params, outputs, ctx):
        structure = outputs["structure"]
        ok = isinstance(structure, ProteinStructure) and len(structure.ca_coordinates) > 0
        return [
            VerificationRecord(
                "protein-pdb-import-shape",
                EvidenceKind.EXPERIMENTAL,
                "PDB importer produced one typed C-alpha coordinate per sequence residue",
                VerificationState.PASS if ok else VerificationState.FAIL,
                "typed object length consistency",
                {"residues": len(structure.ca_coordinates) if ok else 0},
                notes=("Import/schema verification only; not evidence that the predicted fold is physically correct.",),
            )
        ]


class ProteinCoarseFoldSearch(Module):
    metadata = ModuleMetadata(
        "protein.coarse_fold_search",
        "Low-Cost Protein Fold Search",
        "0.1.0",
        "Protein Science",
        "Seeded C-alpha simulated-annealing search reporting the lowest coarse energy found.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Energy is a simplified demonstrator, not a validated molecular force field.",
            "The search does not prove a global minimum or native conformation.",
        ),
    )
    inputs = (
        PortSpec("sequence", "protein_sequence"),
        PortSpec("initial_structure", "protein_structure", required=False),
    )
    outputs = (
        PortSpec("structure", "protein_structure"),
        PortSpec("best_energy", "number"),
        PortSpec("energy_trace", "array"),
        PortSpec("global_minimum_claim", "boolean"),
        PortSpec("energy_model", "string"),
    )
    parameters = (
        ParameterSpec("steps", "integer", 1200),
        ParameterSpec("start_temperature", "number", 1.5),
        ParameterSpec("end_temperature", "number", 0.03),
        ParameterSpec("max_pivot_angle", "number", 0.7, unit="rad"),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "Supports a low-cost single-chain C-alpha approximation only.",
            "Reported energy is a model score, not physical free energy.",
            "Best result is the lowest found by this seeded search, never a guaranteed global minimum.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        sequence = inputs["sequence"]
        if not isinstance(sequence, ProteinSequence):
            raise ValidationError("sequence input must be a ProteinSequence")
        if len(sequence.sequence) > 512:
            raise ValidationError(
                "built-in low-cost fold search is limited to 512 residues; use an external/local high-capacity backend for larger proteins"
            )
        initial = inputs.get("initial_structure")
        if initial is not None:
            if not isinstance(initial, ProteinStructure):
                raise ValidationError("initial_structure must be a ProteinStructure")
            if initial.sequence.sequence != sequence.sequence:
                raise ValidationError("initial structure sequence must match sequence input")
            if len(set(initial.chain_ids)) > 1:
                raise ValidationError("built-in coarse fold search currently supports one chain")
        p = self.resolved_params(params)
        steps = int(p["steps"])
        start_temperature = float(p["start_temperature"])
        end_temperature = float(p["end_temperature"])
        max_angle = float(p["max_pivot_angle"])
        if not 1 <= steps <= 50_000:
            raise ValidationError("steps must be in 1..50000")
        if not math.isfinite(start_temperature) or start_temperature <= 0.0:
            raise ValidationError("start_temperature must be finite and positive")
        if not math.isfinite(end_temperature) or end_temperature <= 0.0:
            raise ValidationError("end_temperature must be finite and positive")
        if not math.isfinite(max_angle) or max_angle <= 0.0:
            raise ValidationError("max_pivot_angle must be finite and positive")

    def execute(self, inputs, params, ctx):
        sequence: ProteinSequence = inputs["sequence"]
        initial = inputs.get("initial_structure")
        best, energy, trace = search_coarse_fold(
            sequence.sequence,
            seed=ctx.seed,
            steps=int(params["steps"]),
            initial_coordinates=(
                np.asarray(initial.ca_coordinates, dtype=float)
                if isinstance(initial, ProteinStructure)
                else None
            ),
            start_temperature=float(params["start_temperature"]),
            end_temperature=float(params["end_temperature"]),
            max_angle=float(params["max_pivot_angle"]),
        )
        provenance = ThirdPartyAssetMetadata(
            source="cace:protein.coarse_fold_search",
            license_id="CACE-project-license",
            attribution="CACE low-cost coarse folding demonstrator",
            notes=(f"seed={ctx.seed}",),
        )
        structure = ProteinStructure(
            sequence=sequence,
            ca_coordinates=tuple(tuple(float(v) for v in row) for row in best),
            provenance=provenance,
            method="cace-ca-coarse-simulated-annealing-v1",
            limitations=(
                "Lowest energy found only; no global-minimum claim.",
                "C-alpha proxy energy is not a molecular force field or free-energy calculation.",
            ),
        )
        return {
            "structure": structure,
            "best_energy": energy,
            "energy_trace": trace,
            "global_minimum_claim": False,
            "energy_model": "cace-ca-bond-clash-hydrophobic-compactness-v1",
        }

    def verify(self, inputs, params, outputs, ctx):
        structure = outputs["structure"]
        coords = np.asarray(structure.ca_coordinates, dtype=float)
        recomputed = coarse_protein_energy(structure.sequence.sequence, coords)
        energy_ok = math.isclose(
            float(outputs["best_energy"]), recomputed, rel_tol=1e-10, abs_tol=1e-10
        )
        trace = np.asarray(outputs["energy_trace"], dtype=float)
        monotone_best = bool(np.all(np.diff(trace) <= 1e-12))
        claim_ok = outputs.get("global_minimum_claim") is False
        return [
            VerificationRecord(
                "coarse-fold-energy-recompute",
                EvidenceKind.NUMERICAL,
                "reported best coarse energy recomputes from the returned C-alpha structure",
                VerificationState.PASS if energy_ok else VerificationState.FAIL,
                "independent coarse-energy recomputation",
                {"reported": float(outputs["best_energy"]), "recomputed": recomputed},
            ),
            VerificationRecord(
                "coarse-fold-best-trace",
                EvidenceKind.NUMERICAL,
                "best-so-far energy trace is non-increasing and no global-minimum claim is emitted",
                VerificationState.PASS if monotone_best and claim_ok else VerificationState.FAIL,
                "trace monotonicity plus explicit claim guard",
                {"global_minimum_claim": bool(outputs.get("global_minimum_claim"))},
            ),
        ]


class SafeHomeLabExperimentModule(Module):
    metadata = ModuleMetadata(
        "chemistry.safe_home_lab",
        "Safe Home Lab Experiment",
        "0.1.0",
        "Chemistry",
        "Return one low-risk whitelist experiment template; unsupported chemistry fails closed.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("experiment_plan", "home_lab_plan"),)
    parameters = (ParameterSpec("experiment_id", "string", "red_cabbage_indicator"),)
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL},
        unit_tests=True,
        documentation=True,
        limitations=[
            "Whitelist is intentionally narrow and does not certify arbitrary household chemicals as safe.",
            "Unsupported requests should be handled as simulation-only rather than improvised procedures.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        try:
            safe_home_experiment(str(self.resolved_params(params)["experiment_id"]))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        return {"experiment_plan": safe_home_experiment(str(params["experiment_id"]))}


class MaterialCandidateSearchModule(Module):
    metadata = ModuleMetadata(
        "materials.descriptor_search",
        "Mathematical Materials Candidate Search",
        "0.1.0",
        "Materials Research",
        "Enumerate binary stoichiometries and rank them with transparent descriptor scores.",
        Maturity.EXPERIMENTAL,
        assumptions=(
            "Initial descriptor model is heuristic screening only.",
            "No synthesis procedure or experimentally validated property is inferred.",
        ),
    )
    outputs = (PortSpec("candidates", "material_candidates"),)
    parameters = (
        ParameterSpec("elements_csv", "string", "Al,O,Si,Mg"),
        ParameterSpec("target", "string", "balanced"),
        ParameterSpec("max_stoich", "integer", 3),
        ParameterSpec("limit", "integer", 12),
    )
    proof_status = ProofStatus(
        evidence={EvidenceKind.EXPERIMENTAL, EvidenceKind.NUMERICAL},
        unit_tests=True,
        property_tests=True,
        documentation=True,
        limitations=[
            "Descriptor ranking is not a materials-property predictor or synthesis guarantee.",
            "Initial built-in element descriptor table is intentionally small.",
        ],
    )

    def validate(self, inputs, params):
        super().validate(inputs, params)
        p = self.resolved_params(params)
        elements = tuple(item.strip() for item in str(p["elements_csv"]).split(",") if item.strip())
        try:
            search_material_candidates(
                elements,
                target=str(p["target"]),
                max_stoich=int(p["max_stoich"]),
                limit=int(p["limit"]),
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        elements = tuple(item.strip() for item in str(params["elements_csv"]).split(",") if item.strip())
        candidates = search_material_candidates(
            elements,
            target=str(params["target"]),
            max_stoich=int(params["max_stoich"]),
            limit=int(params["limit"]),
        )
        return {"candidates": candidates}

    def verify(self, inputs, params, outputs, ctx):
        candidates = outputs["candidates"]
        finite = all(math.isfinite(float(item.score)) for item in candidates)
        no_synthesis = all(item.to_dict()["synthesis_instructions"] is False for item in candidates)
        return [
            VerificationRecord(
                "materials-descriptor-ranking",
                EvidenceKind.NUMERICAL,
                "candidate descriptor scores are finite and carry no synthesis instructions",
                VerificationState.PASS if finite and no_synthesis else VerificationState.FAIL,
                "finite-score and output-policy checks",
                {"candidate_count": len(candidates), "target": str(params["target"])},
                notes=("Heuristic screening only; not a discovery or measured-property claim.",),
            )
        ]


class PhysicsCanvasObjectModule(Module):
    metadata = ModuleMetadata(
        "physics.canvas_object",
        "Physics Canvas Object",
        "0.1.0",
        "Physics",
        "Create a typed established or explicitly theoretical physics object for canvas use.",
        Maturity.EXPERIMENTAL,
    )
    outputs = (PortSpec("physics_object", "physics_object"),)
    parameters = (ParameterSpec("object_id", "string", "electron"),)

    def validate(self, inputs, params):
        super().validate(inputs, params)
        try:
            physics_canvas_object(str(self.resolved_params(params)["object_id"]))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def execute(self, inputs, params, ctx):
        return {"physics_object": physics_canvas_object(str(params["object_id"]))}


def register_molecular_materials(registry) -> None:
    for cls in (
        AtomObjectModule,
        MoleculeJSONModule,
        ProteinSequenceModule,
        AlphaFoldPDBImportModule,
        ProteinCoarseFoldSearch,
        SafeHomeLabExperimentModule,
        MaterialCandidateSearchModule,
        PhysicsCanvasObjectModule,
    ):
        registry.register(cls)
