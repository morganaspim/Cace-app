from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_generator():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/generate_ai_indexes.py"
    spec = importlib.util.spec_from_file_location("cace_generate_ai_indexes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ai_index_generation_is_deterministic_and_self_describing() -> None:
    gen = _load_generator()
    first = gen.render_outputs()
    second = gen.render_outputs()
    assert first == second
    assert set(first) == {
        "MODULE_CATALOG.json",
        "CLAIM_CATALOG.json",
        "LEAN_IMPORT_GRAPH.json",
        "SOURCE_INDEX.json",
        "generated/CACE_SOURCE_CONTEXT.txt",
    }
    assert "PROOF_DEPENDENCY_GRAPH.json" not in first

    modules = json.loads(first["MODULE_CATALOG.json"])
    module_ids = [item["module_id"] for item in modules["modules"]]
    assert module_ids == sorted(module_ids)
    assert len(module_ids) == len(set(module_ids)) == modules["module_count"]
    assert "not verification evidence" in modules["artifact_role"]

    claims = json.loads(first["CLAIM_CATALOG.json"])
    claim_ids = [item["claim_id"] for item in claims["claims"]]
    assert claim_ids == sorted(claim_ids)
    assert len(claim_ids) == claims["claim_count"]
    assert claims["canonical_source"] == "cace_studio/data/claim_registry.json"

    import_graph = json.loads(first["LEAN_IMPORT_GRAPH.json"])
    node_ids = {item["id"] for item in import_graph["nodes"]}
    assert len(node_ids) == import_graph["node_count"]
    assert all(edge["from"] in node_ids and edge["to"] in node_ids for edge in import_graph["edges"])
    assert import_graph["edge_count"] == len(import_graph["edges"])
    assert import_graph["schema"] == "cace-lean-import-graph-v1"
    assert "not theorem dependency" in import_graph["artifact_role"]

    source_index = json.loads(first["SOURCE_INDEX.json"])
    paths = [item["path"] for item in source_index["files"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths)) == source_index["file_count"]
    assert source_index["hash_algorithm"] == "sha256"
    assert all(len(item["sha256"]) == 64 for item in source_index["files"])

    context = first["generated/CACE_SOURCE_CONTEXT.txt"]
    assert "GENERATED NAVIGATION ONLY" in context
    assert "Do not infer PASS" in context
    assert "LEAN_IMPORT_GRAPH.json" in context
    assert "PROOF_DEPENDENCY_GRAPH.json is reserved" in context
