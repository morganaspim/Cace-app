#!/usr/bin/env python3
"""Build the verified V330 theorem/assumption DAG from qualification evidence.

Unlike the repository's Lean import graph, this graph is derived from canonical
Lean.Environment theorem metadata and the kernel axiom audit. It is evidence-derived
navigation: it never upgrades qualification state and fails closed on provenance,
endpoint, axiom, binder, or theorem-cycle drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
GRAPH_SCHEMA = "cace-v330-proof-dependency-graph-v1"
ENV_SCHEMA = "cace-lean-theorem-metadata-v3"
AUDIT_FORMAT = "cace.lean-theorem-metadata"


class ProofDependencyGraphError(RuntimeError):
    """Raised when proof-dependency evidence cannot be safely combined."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, separators=(",", ": "))
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProofDependencyGraphError(message)


def _detect_endpoint_cycles(endpoint_names: set[str], dependency_map: dict[str, list[str]]) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(name: str) -> None:
        mark = state.get(name, 0)
        if mark == 2:
            return
        if mark == 1:
            start = stack.index(name)
            cycle = stack[start:] + [name]
            raise ProofDependencyGraphError(
                "endpoint theorem dependency cycle: " + " -> ".join(cycle)
            )
        state[name] = 1
        stack.append(name)
        for dep in dependency_map.get(name, []):
            if dep in endpoint_names:
                visit(dep)
        stack.pop()
        state[name] = 2

    for name in sorted(endpoint_names):
        visit(name)


def _load_contract():
    from cace_studio.core.proof_contract import ProofContractRegistry

    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    if contract is None:
        raise ProofDependencyGraphError(f"missing canonical proof contract: {CLAIM_ID}")
    return contract


def build_graph(
    *,
    environment_metadata: dict[str, Any],
    environment_metadata_bytes: bytes,
    kernel_axiom_audit: dict[str, Any],
    kernel_axiom_audit_bytes: bytes,
    contract=None,
) -> dict[str, Any]:
    contract = contract or _load_contract()
    expected = set(contract.endpoint_theorems)
    allowed_axioms = set(contract.allowed_axioms)

    _require(environment_metadata.get("artifact_schema") == ENV_SCHEMA, "unsupported environment metadata schema")
    _require(environment_metadata.get("metadata_state") == "LEAN_GENERATED", "environment metadata is not LEAN_GENERATED")
    _require(environment_metadata.get("provenance") == "Lean.Environment", "environment metadata provenance mismatch")
    _require(environment_metadata.get("claim_id") == contract.claim_id, "environment claim_id differs from proof contract")
    _require(environment_metadata.get("proof_contract_id") == contract.contract_id, "environment proof_contract_id differs from proof contract")
    _require(environment_metadata.get("proof_contract_sha256") == contract.contract_sha256, "environment proof_contract_sha256 differs from proof contract")
    _require(environment_metadata.get("mathlib_commit") == contract.dependency_pins.get("mathlib_commit"), "environment Mathlib pin differs from proof contract")

    endpoints = environment_metadata.get("endpoints")
    _require(isinstance(endpoints, list), "environment endpoints must be an array")
    endpoint_by_name: dict[str, dict[str, Any]] = {}
    for record in endpoints:
        _require(isinstance(record, dict), "environment endpoint record must be an object")
        name = record.get("theorem")
        _require(isinstance(name, str) and bool(name), "environment theorem name must be non-empty")
        _require(name not in endpoint_by_name, f"duplicate environment theorem record: {name}")
        binders = record.get("binders")
        _require(isinstance(binders, list), f"{name}: canonical binders are missing")
        for index, binder in enumerate(binders):
            _require(isinstance(binder, dict), f"{name}: binder {index} must be an object")
            _require(binder.get("index") == index, f"{name}: binder index drift at {index}")
            _require(isinstance(binder.get("is_proposition"), bool), f"{name}: binder {index} proposition flag missing")
            _require(isinstance(binder.get("type_pp_all"), str) and bool(binder["type_pp_all"]), f"{name}: binder {index} type missing")
        endpoint_by_name[name] = record
    _require(set(endpoint_by_name) == expected, "environment endpoint set differs from proof contract")
    _require(environment_metadata.get("endpoint_count") == len(expected), "environment endpoint_count mismatch")

    expected_audit_sha = environment_metadata.get("kernel_axiom_audit_sha256")
    _require(isinstance(expected_audit_sha, str) and len(expected_audit_sha) == 64, "environment kernel audit SHA is malformed")
    _require(_sha256(kernel_axiom_audit_bytes) == expected_audit_sha, "kernel axiom audit bytes do not match environment binding")
    _require(kernel_axiom_audit.get("format") == AUDIT_FORMAT, "unsupported kernel axiom audit format")
    audit_records = kernel_axiom_audit.get("theorems")
    _require(isinstance(audit_records, list), "kernel axiom audit theorems must be an array")
    audit_by_name: dict[str, tuple[str, ...]] = {}
    for record in audit_records:
        _require(isinstance(record, dict), "kernel axiom audit theorem record must be an object")
        name = record.get("name")
        axioms = record.get("axioms")
        _require(isinstance(name, str) and bool(name), "kernel axiom audit theorem name must be non-empty")
        _require(name not in audit_by_name, f"duplicate kernel axiom audit theorem: {name}")
        _require(isinstance(axioms, list) and all(isinstance(item, str) and item for item in axioms), f"{name}: malformed axiom list")
        _require(len(axioms) == len(set(axioms)), f"{name}: duplicate axiom dependency")
        forbidden = sorted(set(axioms) - allowed_axioms)
        _require("sorryAx" not in axioms and "Lean.ofReduceBool" not in forbidden, f"{name}: proof contains forbidden kernel escape axiom")
        _require(not forbidden, f"{name}: non-whitelisted axioms: {forbidden}")
        audit_by_name[name] = tuple(sorted(axioms))
    _require(set(audit_by_name) == expected, "kernel axiom audit theorem set differs from proof contract")
    _require(kernel_axiom_audit.get("theorem_count") == len(expected), "kernel axiom audit theorem_count mismatch")
    _require(environment_metadata.get("kernel_axiom_audit_theorem_count") == len(expected), "environment kernel audit theorem_count mismatch")

    dependency_map = {
        name: list(record.get("direct_cace_theorem_dependencies", []))
        for name, record in endpoint_by_name.items()
    }
    for name, deps in dependency_map.items():
        _require(all(isinstance(dep, str) and dep for dep in deps), f"{name}: malformed direct dependency")
        _require(name not in deps, f"{name}: self-dependency is forbidden")
    _detect_endpoint_cycles(expected, dependency_map)

    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()

    def add_node(node_id: str, *, kind: str, classification: str, **extra: Any) -> None:
        candidate = {"id": node_id, "kind": kind, "classification": classification, **extra}
        current = nodes.get(node_id)
        if current is None:
            nodes[node_id] = candidate
        elif current != candidate and current.get("classification") != "discharged":
            raise ProofDependencyGraphError(f"conflicting node classification: {node_id}")

    for theorem in sorted(expected):
        record = endpoint_by_name[theorem]
        add_node(theorem, kind="theorem", classification="discharged", endpoint=True)

        for dep in sorted(record.get("direct_cace_theorem_dependencies", [])):
            if dep in expected:
                add_node(dep, kind="theorem", classification="discharged", endpoint=True)
            else:
                add_node(dep, kind="declaration", classification="internal_verified_declaration")
            edges.add((theorem, dep, "proof_dependency"))

        for const in sorted(record.get("statement_constants", [])):
            if const == theorem:
                continue
            if const in expected:
                add_node(const, kind="theorem", classification="discharged", endpoint=True)
            elif const in allowed_axioms:
                add_node(const, kind="axiom", classification="external_allowed_axiom")
            elif const.startswith("CACEFormal."):
                add_node(const, kind="declaration", classification="internal_verified_declaration")
            else:
                add_node(const, kind="declaration", classification="external_verified")
            edges.add((theorem, const, "statement_constant"))

        for binder in record["binders"]:
            binder_id = f"{theorem}#binder:{binder['index']}:{binder['name']}"
            proposition = binder["is_proposition"]
            add_node(
                binder_id,
                kind="binder",
                classification="conditional_open" if proposition else "parameter",
                theorem=theorem,
                binder_index=binder["index"],
                binder_name=binder["name"],
                binder_info=binder["binder_info"],
                type_pp_all=binder["type_pp_all"],
                constants=sorted(binder.get("constants", [])),
            )
            edges.add((theorem, binder_id, "conditional_binder" if proposition else "parameter"))

        for axiom in audit_by_name[theorem]:
            add_node(axiom, kind="axiom", classification="external_allowed_axiom")
            edges.add((theorem, axiom, "axiom_dependency"))

    rendered_edges = [
        {"from": source, "to": target, "kind": kind}
        for source, target, kind in sorted(edges)
    ]
    rendered_nodes = [nodes[node_id] for node_id in sorted(nodes)]
    classifications: dict[str, int] = {}
    for node in rendered_nodes:
        key = str(node["classification"])
        classifications[key] = classifications.get(key, 0) + 1

    return {
        "schema": GRAPH_SCHEMA,
        "artifact_role": "evidence-derived proof navigation; never upgrades qualification state",
        "claim_id": contract.claim_id,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "git_commit": environment_metadata["git_commit"],
        "lean_version": environment_metadata["lean_version"],
        "lean_toolchain": environment_metadata["lean_toolchain"],
        "mathlib_commit": environment_metadata["mathlib_commit"],
        "source_artifacts": {
            "environment_metadata_sha256": _sha256(environment_metadata_bytes),
            "kernel_axiom_audit_sha256": _sha256(kernel_axiom_audit_bytes),
        },
        "node_count": len(rendered_nodes),
        "edge_count": len(rendered_edges),
        "classification_counts": dict(sorted(classifications.items())),
        "nodes": rendered_nodes,
        "edges": rendered_edges,
    }


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    try:
        value = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ProofDependencyGraphError(f"malformed JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProofDependencyGraphError(f"{path} must contain a JSON object")
    return value, data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-metadata", type=Path, required=True)
    parser.add_argument("--kernel-axiom-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        environment, environment_bytes = _read_json(args.environment_metadata)
        audit, audit_bytes = _read_json(args.kernel_axiom_audit)
        graph = build_graph(
            environment_metadata=environment,
            environment_metadata_bytes=environment_bytes,
            kernel_axiom_audit=audit,
            kernel_axiom_audit_bytes=audit_bytes,
        )
    except (OSError, ValueError, ProofDependencyGraphError) as exc:
        print(f"proof dependency graph rejected: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_json_bytes(graph)
    args.output.write_bytes(rendered)
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        f"{_sha256(rendered)}  {args.output.name}\n", encoding="utf-8"
    )
    print(f"Proof dependency graph PASS: {graph['node_count']} nodes, {graph['edge_count']} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
