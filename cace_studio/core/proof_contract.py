from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any, Mapping
import json

from .reproducibility import sha256_identity


_ALLOWED_DEPENDENCY_STATES = {
    "NOT_GENERATED",
    "SOURCE_IMPORT_CLOSURE_ONLY",
    "LEAN_GENERATED",
}


def _nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _strings(raw: Any, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item.strip() for item in raw):
        raise ValueError(f"{field_name} must be an array of non-empty strings")
    values = tuple(item.strip() for item in raw)
    if not allow_empty and not values:
        raise ValueError(f"{field_name} must not be empty")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def _relative_source(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".lean":
        raise ValueError(f"audited source must be a relative .lean path: {value!r}")
    return value


@dataclass(frozen=True)
class ProofContract:
    contract_id: str
    claim_id: str
    formal_system: str
    build_target: str
    toolchain_file: str
    dependency_pins: Mapping[str, str]
    endpoint_theorems: tuple[str, ...]
    audited_source_files: tuple[str, ...]
    allowed_axioms: tuple[str, ...]
    required_checks: tuple[str, ...]
    nonclaims: tuple[str, ...]
    theorem_dependency_metadata_state: str
    theorem_dependency_metadata_note: str
    contract_sha256: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ProofContract":
        if not isinstance(raw, Mapping):
            raise ValueError("proof contract must be an object")
        dependency_pins_raw = raw.get("dependency_pins")
        if not isinstance(dependency_pins_raw, Mapping) or not dependency_pins_raw:
            raise ValueError("dependency_pins must be a non-empty object")
        dependency_pins = {
            _nonempty(str(key), "dependency pin name"): _nonempty(value, f"dependency pin {key}")
            for key, value in dependency_pins_raw.items()
        }
        metadata = raw.get("theorem_dependency_metadata")
        if not isinstance(metadata, Mapping):
            raise ValueError("theorem_dependency_metadata must be an object")
        state = _nonempty(metadata.get("state"), "theorem dependency metadata state")
        if state not in _ALLOWED_DEPENDENCY_STATES:
            raise ValueError(f"unsupported theorem dependency metadata state: {state}")
        note = _nonempty(metadata.get("note"), "theorem dependency metadata note")

        endpoints = _strings(raw.get("endpoint_theorems"), "endpoint_theorems")
        if any("." not in theorem for theorem in endpoints):
            raise ValueError("endpoint_theorems must use fully-qualified Lean names")
        sources = tuple(
            _relative_source(value)
            for value in _strings(raw.get("audited_source_files"), "audited_source_files")
        )
        payload = {
            "contract_id": _nonempty(raw.get("contract_id"), "contract_id"),
            "claim_id": _nonempty(raw.get("claim_id"), "claim_id"),
            "formal_system": _nonempty(raw.get("formal_system"), "formal_system"),
            "build_target": _nonempty(raw.get("build_target"), "build_target"),
            "toolchain_file": _nonempty(raw.get("toolchain_file"), "toolchain_file"),
            "dependency_pins": dependency_pins,
            "endpoint_theorems": list(endpoints),
            "audited_source_files": list(sources),
            "allowed_axioms": list(_strings(raw.get("allowed_axioms"), "allowed_axioms", allow_empty=True)),
            "required_checks": list(_strings(raw.get("required_checks"), "required_checks")),
            "nonclaims": list(_strings(raw.get("nonclaims"), "nonclaims")),
            "theorem_dependency_metadata": {"state": state, "note": note},
        }
        return cls(
            contract_id=payload["contract_id"],
            claim_id=payload["claim_id"],
            formal_system=payload["formal_system"],
            build_target=payload["build_target"],
            toolchain_file=payload["toolchain_file"],
            dependency_pins=dict(dependency_pins),
            endpoint_theorems=endpoints,
            audited_source_files=sources,
            allowed_axioms=tuple(payload["allowed_axioms"]),
            required_checks=tuple(payload["required_checks"]),
            nonclaims=tuple(payload["nonclaims"]),
            theorem_dependency_metadata_state=state,
            theorem_dependency_metadata_note=note,
            contract_sha256=sha256_identity(payload),
        )

    def payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "claim_id": self.claim_id,
            "formal_system": self.formal_system,
            "build_target": self.build_target,
            "toolchain_file": self.toolchain_file,
            "dependency_pins": dict(self.dependency_pins),
            "endpoint_theorems": list(self.endpoint_theorems),
            "audited_source_files": list(self.audited_source_files),
            "allowed_axioms": list(self.allowed_axioms),
            "required_checks": list(self.required_checks),
            "nonclaims": list(self.nonclaims),
            "theorem_dependency_metadata": {
                "state": self.theorem_dependency_metadata_state,
                "note": self.theorem_dependency_metadata_note,
            },
        }


@dataclass(frozen=True)
class ProofContractRegistry:
    schema_version: int
    policy: str
    contracts: tuple[ProofContract, ...]
    registry_sha256: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ProofContractRegistry":
        if not isinstance(raw, Mapping):
            raise ValueError("proof-contract registry must be an object")
        raw_contracts = raw.get("contracts", [])
        if not isinstance(raw_contracts, list):
            raise ValueError("contracts must be an array")
        contracts = tuple(ProofContract.from_mapping(item) for item in raw_contracts)
        seen_ids: set[str] = set()
        seen_claims: set[str] = set()
        for contract in contracts:
            if contract.contract_id in seen_ids:
                raise ValueError(f"duplicate proof contract_id: {contract.contract_id}")
            if contract.claim_id in seen_claims:
                raise ValueError(f"claim has multiple proof contracts: {contract.claim_id}")
            seen_ids.add(contract.contract_id)
            seen_claims.add(contract.claim_id)
        return cls(
            schema_version=int(raw.get("schema_version", 0)),
            policy=str(raw.get("policy", "fail-closed")),
            contracts=contracts,
            registry_sha256=sha256_identity(raw),
        )

    @classmethod
    def load_default(cls) -> "ProofContractRegistry":
        path = files("cace_studio").joinpath("data/proof_contracts.json")
        return cls.from_mapping(json.loads(path.read_text(encoding="utf-8")))

    def by_id(self, contract_id: str) -> ProofContract | None:
        return next((item for item in self.contracts if item.contract_id == contract_id), None)

    def for_claim(self, claim_id: str) -> ProofContract | None:
        return next((item for item in self.contracts if item.claim_id == claim_id), None)
