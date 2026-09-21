from __future__ import annotations

import time

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
    assert payload["modules"]
    module_ids = {item["metadata"]["module_id"] for item in payload["modules"]}
    assert len(module_ids) == len(payload["modules"])


def test_capabilities_are_truthful_browser_adapter():
    payload = web.capabilities()
    assert payload["metadata_is_verification_evidence"] is False
    assert payload["capability_policy_hash"]
    assert payload["registry_contract_hash"]
    assert payload["modules"]

    module = payload["modules"][0]
    if module["inputs"]:
        assert module["inputs"][0]["type"] == module["inputs"][0]["type_name"]
    if module["parameters"]:
        assert module["parameters"][0]["type"] == module["parameters"][0]["type_name"]
    assert module["declared_proof_status"]["is_verified"] is False
    assert "Exact-head qualification requires" in module["declared_proof_status"]["proof_note"]


def test_graph_validation_rejects_unknown_modules_without_throwing():
    payload = {
        "experiment": {
            "schema_version": 2,
            "graph_schema_version": 1,
            "name": "Unknown module",
            "nodes": [
                {
                    "id": "rogue",
                    "module_id": "unqualified.adversarial_solver_v99",
                    "params": {},
                    "position": [0, 0],
                }
            ],
            "edges": [],
            "groups": [],
            "metadata": {},
        }
    }

    result = web.validate_graph(payload)
    assert result["valid"] is False
    assert "unknown module" in result["reason"]
    assert result["node_count"] == 0


def test_alphafold_prediction_wraps_attributed_metadata(monkeypatch):
    def fake_fetch(url):
        assert url.endswith("/Q92793")
        return [
            {
                "entryId": "AF-Q92793-F1",
                "gene": "CREBBP",
                "cifUrl": "https://example.test/model.cif",
                "pdbUrl": "https://example.test/model.pdb",
                "paeDocUrl": "https://example.test/pae.json",
            }
        ]

    monkeypatch.setattr(web, "_fetch_json_url", fake_fetch)
    result = web.alphafold_prediction("q92793")

    assert result["schema"] == "cace-alphafold-prediction-v1"
    assert result["accession"] == "Q92793"
    assert result["urls"]["pdb"].endswith("model.pdb")
    assert "not CACE proof evidence" in result["evidence_note"]


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



def test_local_ai_status_defaults_to_disabled(monkeypatch):
    monkeypatch.setattr(web, "LOCAL_AI_ENABLED", False)
    result = web.local_ai_status()
    assert result["schema"] == "cace-local-ai-status-v1"
    assert result["enabled"] is False
    assert result["provider_health"] == "disabled"
    assert result["boundary"]["ai_network_mode"] == "LOCAL_ZERO_CONTACT"
    assert result["boundary"]["internet_access"] is False


def test_local_ai_recompile_plan_is_plan_only():
    plan = web.local_ai_recompile_plan()
    assert plan["schema"] == "cace-ai-recompile-plan-v1"
    assert plan["status"] == "plan-only"
    assert plan["recompile_is_automatic"] is False
    assert plan["ranked_training_sources"]
    assert "automatic proof promotion" in plan["forbidden"]
