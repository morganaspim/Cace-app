from __future__ import annotations

import json
from pathlib import Path

from .graph import Edge, Experiment, ExperimentGroup, Node

# .cace container schema. This is intentionally independent from
# Experiment.schema_version, which identifies the scientific graph data model.
CURRENT_SCHEMA = 2
SUPPORTED_SCHEMAS = {1, 2}


def _validate_groups(exp: Experiment) -> None:
    node_ids = {node.id for node in exp.nodes}
    seen_group_ids: set[str] = set()
    grouped_nodes: set[str] = set()
    for group in exp.groups:
        if group.id in seen_group_ids:
            raise ValueError(f"duplicate experiment group id: {group.id}")
        seen_group_ids.add(group.id)
        missing = sorted(set(group.node_ids) - node_ids)
        if missing:
            raise ValueError(f"group {group.id!r} references missing nodes: {missing}")
        overlap = sorted(grouped_nodes & set(group.node_ids))
        if overlap:
            raise ValueError(
                f"nodes may belong to only one experiment group in schema v2: {overlap}"
            )
        grouped_nodes.update(group.node_ids)


def save_experiment(exp: Experiment, path: str | Path) -> None:
    _validate_groups(exp)
    data = {
        "schema_version": CURRENT_SCHEMA,
        "graph_schema_version": exp.schema_version,
        "name": exp.name,
        "nodes": [
            {
                "id": n.id,
                "module_id": n.module_id,
                "params": n.params,
                "position": list(n.position),
            }
            for n in exp.nodes
        ],
        "edges": [e.__dict__ for e in exp.edges],
        "groups": [
            {
                "id": group.id,
                "name": group.name,
                "node_ids": list(group.node_ids),
            }
            for group in exp.groups
        ],
        "metadata": exp.metadata,
    }
    Path(path).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n\n",
        encoding="utf-8",
    )


def load_experiment(path: str | Path) -> Experiment:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    container_schema = data.get("schema_version")
    if container_schema not in SUPPORTED_SCHEMAS:
        raise ValueError(f"unsupported experiment schema: {container_schema}")

    if container_schema == 1:
        graph_schema_version = 1
        raw_groups = []
    else:
        graph_schema_version = int(data.get("graph_schema_version", 1))
        raw_groups = data.get("groups", [])
        if not isinstance(raw_groups, list):
            raise ValueError("experiment groups must be an array")

    exp = Experiment(
        schema_version=graph_schema_version,
        name=data.get("name", "Untitled"),
        nodes=[
            Node(
                id=n["id"],
                module_id=n["module_id"],
                params=n.get("params", {}),
                position=tuple(n.get("position", (0, 0))),
            )
            for n in data.get("nodes", [])
        ],
        edges=[Edge(**e) for e in data.get("edges", [])],
        metadata=data.get("metadata", {}),
        groups=[
            ExperimentGroup(
                id=str(group["id"]),
                name=str(group["name"]),
                node_ids=tuple(str(node_id) for node_id in group.get("node_ids", [])),
            )
            for group in raw_groups
        ],
    )
    _validate_groups(exp)
    return exp
