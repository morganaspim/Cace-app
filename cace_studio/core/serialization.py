from __future__ import annotations
import json
from pathlib import Path
from .graph import Experiment, Node, Edge

CURRENT_SCHEMA = 1

def save_experiment(exp: Experiment, path: str | Path) -> None:
    data = {
        "schema_version": CURRENT_SCHEMA,
        "name": exp.name,
        "nodes": [{"id": n.id, "module_id": n.module_id, "params": n.params, "position": list(n.position)} for n in exp.nodes],
        "edges": [e.__dict__ for e in exp.edges],
        "metadata": exp.metadata,
    }
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n\n", encoding="utf-8")

def load_experiment(path: str | Path) -> Experiment:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != CURRENT_SCHEMA:
        raise ValueError(f"unsupported experiment schema: {data.get('schema_version')}")
    return Experiment(schema_version=CURRENT_SCHEMA, name=data.get("name", "Untitled"),
        nodes=[Node(id=n["id"], module_id=n["module_id"], params=n.get("params", {}), position=tuple(n.get("position", (0,0)))) for n in data.get("nodes", [])],
        edges=[Edge(**e) for e in data.get("edges", [])], metadata=data.get("metadata", {}))
