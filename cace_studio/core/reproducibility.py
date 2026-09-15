from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .graph import Edge, Experiment


def _normalize(value: Any) -> Any:
    """Normalize supported values into a deterministic JSON data model.

    Reproducibility identities fail closed on unsupported or non-finite values
    rather than falling back to repr(), which may be process- or platform-specific.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not allowed in reproducibility identities")
        return value
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("reproducibility mappings require string keys")
            normalized[key] = _normalize(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_normalize(item) for item in value]
        return sorted(items, key=lambda item: canonical_json_text(item))
    raise TypeError(f"unsupported reproducibility value: {type(value).__name__}")


def canonical_json_text(value: Any) -> str:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_text(value).encode("utf-8")


def sha256_identity(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _edge_tuple(edge: Edge) -> tuple[str, str, str, str]:
    return (edge.source_node, edge.source_port, edge.target_node, edge.target_port)


def _groups_payload(experiment: Experiment) -> list[dict[str, Any]]:
    return [
        {
            "id": group.id,
            "name": group.name,
            "node_ids": sorted(group.node_ids),
        }
        for group in sorted(experiment.groups, key=lambda item: item.id)
    ]


def experiment_payload(experiment: Experiment, *, include_layout: bool) -> dict[str, Any]:
    nodes = []
    for node in sorted(experiment.nodes, key=lambda item: item.id):
        payload: dict[str, Any] = {
            "id": node.id,
            "module_id": node.module_id,
            "params": _normalize(node.params),
        }
        if include_layout:
            payload["position"] = [float(node.position[0]), float(node.position[1])]
        nodes.append(payload)
    edges = [
        {
            "source_node": edge.source_node,
            "source_port": edge.source_port,
            "target_node": edge.target_node,
            "target_port": edge.target_port,
        }
        for edge in sorted(experiment.edges, key=_edge_tuple)
    ]
    payload = {
        "schema_version": experiment.schema_version,
        "nodes": nodes,
        "edges": edges,
    }
    if include_layout:
        payload["name"] = experiment.name
        payload["metadata"] = _normalize(experiment.metadata)
        payload["groups"] = _groups_payload(experiment)
    return payload


def experiment_fingerprint(experiment: Experiment, *, include_layout: bool = False) -> str:
    return sha256_identity(experiment_payload(experiment, include_layout=include_layout))


def _port_payload(port) -> dict[str, Any]:
    return {
        "name": port.name,
        "type_name": port.type_name,
        "required": bool(port.required),
        "unit": port.unit,
    }


def _parameter_payload(parameter) -> dict[str, Any]:
    return {
        "name": parameter.name,
        "type_name": parameter.type_name,
        "default": _normalize(parameter.default),
        "description": parameter.description,
        "unit": parameter.unit,
    }


def registry_contract_payload(registry) -> dict[str, Any]:
    modules = []
    for cls in sorted(registry.classes(), key=lambda item: item.metadata.module_id):
        metadata = cls.metadata
        proof = cls.proof_status
        modules.append(
            {
                "module_id": metadata.module_id,
                "name": metadata.name,
                "version": metadata.version,
                "category": metadata.category,
                "description": metadata.description,
                "maturity": metadata.maturity.value,
                "assumptions": list(metadata.assumptions),
                "inputs": [_port_payload(port) for port in cls.inputs],
                "outputs": [_port_payload(port) for port in cls.outputs],
                "parameters": [_parameter_payload(parameter) for parameter in cls.parameters],
                "supports_gpu": bool(cls.supports_gpu),
                "declared_proof_status": {
                    "evidence": sorted(item.value for item in proof.evidence),
                    "unit_tests": bool(proof.unit_tests),
                    "property_tests": bool(proof.property_tests),
                    "regression_tests": bool(proof.regression_tests),
                    "documentation": bool(proof.documentation),
                    "benchmarked": bool(proof.benchmarked),
                    "formal_artifact": proof.formal_artifact,
                    "limitations": list(proof.limitations),
                },
            }
        )
    return {"contract_schema": 1, "modules": modules}


def registry_contract_fingerprint(registry) -> str:
    return sha256_identity(registry_contract_payload(registry))


def reproducibility_manifest(experiment: Experiment, registry) -> dict[str, Any]:
    module_ids = sorted({node.module_id for node in experiment.nodes})
    return {
        "manifest_schema": 1,
        "identity_algorithm": "sha256/cace-canonical-json-v1",
        "semantic_experiment_sha256": experiment_fingerprint(experiment, include_layout=False),
        "full_experiment_sha256": experiment_fingerprint(experiment, include_layout=True),
        "module_contract_sha256": registry_contract_fingerprint(registry),
        "node_count": len(experiment.nodes),
        "edge_count": len(experiment.edges),
        "group_count": len(experiment.groups),
        "module_ids": module_ids,
        "notes": [
            "semantic identity excludes experiment name, metadata, node positions and organizational groups",
            "full identity includes layout/name/metadata/groups",
            "module-contract identity includes declared port/parameter units",
            "these hashes establish content identity, not scientific correctness",
        ],
    }


def _node_semantics(experiment: Experiment) -> dict[str, tuple[str, Any]]:
    return {
        node.id: (node.module_id, _normalize(node.params))
        for node in experiment.nodes
    }


def _positions(experiment: Experiment) -> dict[str, tuple[float, float]]:
    return {
        node.id: (float(node.position[0]), float(node.position[1]))
        for node in experiment.nodes
    }


def drift_report(expected: Experiment, actual: Experiment) -> dict[str, Any]:
    before_nodes = _node_semantics(expected)
    after_nodes = _node_semantics(actual)
    before_ids = set(before_nodes)
    after_ids = set(after_nodes)
    shared = before_ids & after_ids
    changed_nodes = sorted(
        node_id for node_id in shared if before_nodes[node_id] != after_nodes[node_id]
    )

    before_edges = {_edge_tuple(edge) for edge in expected.edges}
    after_edges = {_edge_tuple(edge) for edge in actual.edges}

    before_positions = _positions(expected)
    after_positions = _positions(actual)
    layout_changed_nodes = sorted(
        node_id
        for node_id in (before_ids & after_ids)
        if before_positions[node_id] != after_positions[node_id]
    )

    semantic_before = experiment_fingerprint(expected, include_layout=False)
    semantic_after = experiment_fingerprint(actual, include_layout=False)
    full_before = experiment_fingerprint(expected, include_layout=True)
    full_after = experiment_fingerprint(actual, include_layout=True)
    semantic_equal = semantic_before == semantic_after
    full_equal = full_before == full_after

    return {
        "drift_schema": 1,
        "semantic_equal": semantic_equal,
        "full_equal": full_equal,
        "layout_only": semantic_equal and not full_equal,
        "semantic_sha256": {"expected": semantic_before, "actual": semantic_after},
        "full_sha256": {"expected": full_before, "actual": full_after},
        "added_nodes": sorted(after_ids - before_ids),
        "removed_nodes": sorted(before_ids - after_ids),
        "changed_nodes": changed_nodes,
        "added_edges": [list(edge) for edge in sorted(after_edges - before_edges)],
        "removed_edges": [list(edge) for edge in sorted(before_edges - after_edges)],
        "layout_changed_nodes": layout_changed_nodes,
        "groups_changed": _groups_payload(expected) != _groups_payload(actual),
        "name_changed": expected.name != actual.name,
        "metadata_changed": _normalize(expected.metadata) != _normalize(actual.metadata),
        "interpretation": (
            "identical"
            if full_equal
            else "layout-or-presentation-only"
            if semantic_equal
            else "scientific-graph-semantic-change"
        ),
        "evidence_note": "drift classification is provenance metadata, not verification evidence",
    }
