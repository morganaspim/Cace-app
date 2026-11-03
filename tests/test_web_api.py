from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from api import index as web


def _empty_experiment() -> dict:
    return {
        "schema_version": 2,
        "graph_schema_version": 1,
        "name": "Browser Smoke",
        "nodes": [],
        "edges": [],
        "groups": [],
        "metadata": {},
    }


def test_browser_assets_and_registry_are_available():
    assert (web.WEB_ROOT / "index.html").is_file()
    assert (web.WEB_ROOT / "studio.css").is_file()
    assert (web.WEB_ROOT / "studio.js").is_file()

    health = web.health()
    assert health["status"] == "ok"
    assert health["surface"] == "browser"

    payload = web.modules()
    assert payload["metadata_is_verification_evidence"] is False
    assert payload["default_hidden"] is True
    assert payload["modules"]
    module_ids = {item["metadata"]["module_id"] for item in payload["modules"]}
    assert len(module_ids) == len(payload["modules"])
    assert "core.constant" in module_ids
    assert "core.add" in module_ids
    assert "formal325.mesh_certificate_generator" not in module_ids

    capabilities = web.capabilities()
    assert capabilities["schema"] == "cace-qualified-capabilities-v1"
    assert capabilities["surface"] == "ui"
    assert capabilities["proof_effect"] == "none"


def test_browser_experiment_payload_preserves_layout_groups_and_params():
    module_id = web.modules()["modules"][0]["metadata"]["module_id"]
    payload = {
        "schema_version": 2,
        "graph_schema_version": 1,
        "name": "Web graph",
        "nodes": [
            {
                "id": "n_a",
                "module_id": module_id,
                "params": {"alpha": 2},
                "position": [12.5, 44],
            }
        ],
        "edges": [],
        "groups": [{"id": "g_a", "name": "Example", "node_ids": ["n_a"]}],
        "metadata": {"surface": "browser"},
    }
    exp = web._experiment_from_payload(payload)
    assert exp.name == "Web graph"
    assert exp.nodes[0].position == (12.5, 44.0)
    assert exp.nodes[0].params == {"alpha": 2}
    assert exp.groups[0].node_ids == ("n_a",)
    assert exp.metadata == {"surface": "browser"}


def test_async_browser_run_job_reaches_terminal_state():
    job = web.start_run({"experiment": _empty_experiment(), "seed": 7})
    deadline = time.monotonic() + 5.0
    current = job
    while current["status"] not in {"completed", "cancelled", "failed"}:
        assert time.monotonic() < deadline
        time.sleep(0.01)
        current = web.run_status(job["job_id"])

    assert current["status"] == "completed"
    assert current["result"]["completed"] is True
    assert current["result"]["seed"] == 7
    assert current["result"]["experiment"] == "Browser Smoke"



def test_public_graph_validation_rejects_hidden_engineering_modules():
    hidden = {
        "schema_version": 2,
        "graph_schema_version": 1,
        "name": "Hidden module injection",
        "nodes": [
            {
                "id": "hidden",
                "module_id": "formal325.mesh_certificate_generator",
                "params": {},
                "position": [0, 0],
            }
        ],
        "edges": [],
        "groups": [],
        "metadata": {},
    }
    with pytest.raises(HTTPException) as exc_info:
        web.validate_graph({"experiment": hidden})
    assert exc_info.value.status_code == 400
    assert "unavailable" in str(exc_info.value.detail)


def test_public_graph_validation_accepts_qualified_workflow():
    payload = {
        "schema_version": 2,
        "graph_schema_version": 1,
        "name": "Qualified arithmetic",
        "nodes": [
            {"id": "a", "module_id": "core.constant", "params": {"value": 2}, "position": [0, 0]},
            {"id": "b", "module_id": "core.constant", "params": {"value": 3}, "position": [0, 0]},
            {"id": "sum", "module_id": "core.add", "params": {}, "position": [0, 0]},
        ],
        "edges": [
            {"source_node": "a", "source_port": "value", "target_node": "sum", "target_port": "a"},
            {"source_node": "b", "source_port": "value", "target_node": "sum", "target_port": "b"},
        ],
        "groups": [],
        "metadata": {},
    }
    result = web.validate_graph({"experiment": payload})
    assert result["valid"] is True
    assert result["execution_order"] == ["a", "b", "sum"]
    assert len(result["semantic_experiment_sha256"]) == 64


def test_connection_validation_cannot_bypass_capability_gate():
    with pytest.raises(HTTPException) as exc_info:
        web.validate_connection(
            {
                "source_module_id": "formal325.mesh_certificate_generator",
                "source_port": "certificate",
                "target_module_id": "core.add",
                "target_port": "a",
            }
        )
    assert exc_info.value.status_code == 400
