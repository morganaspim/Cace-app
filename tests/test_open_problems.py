from __future__ import annotations

import json

from cace_studio.modules.open_problem import ResearchOpenProblem
from cace_studio.research.open_problems import OpenProblemCatalog, load_millennium_catalog


def test_packaged_millennium_statuses_match_current_snapshot():
    catalog = load_millennium_catalog()
    counts = {}
    for entry in catalog.entries:
        counts[entry.status] = counts.get(entry.status, 0) + 1
    assert len(catalog.entries) == 7
    assert counts["open"] == 5
    assert counts["active-review"] == 1
    assert counts["solved"] == 1
    navier = catalog.get("clay.navier-stokes")
    assert navier is not None
    assert "apparently been settled" in navier.status_note
    assert len(navier.source_urls) >= 2


def test_duplicate_custom_catalog_ids_fail_closed():
    entry = load_millennium_catalog().entries[0].to_dict()
    payload = {
        "schema": "cace.open-problem-catalog.v1",
        "catalog_id": "dup",
        "entries": [entry, entry],
    }
    try:
        OpenProblemCatalog.from_json_text(json.dumps(payload))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate open-problem IDs must fail closed")


def test_open_problem_module_produces_no_verification_records():
    problem = load_millennium_catalog().entries[0]
    module = ResearchOpenProblem()
    params = problem.to_module_params()
    module.validate({}, params)
    outputs = module.execute({}, params, None)
    assert outputs["problem"]["problem_id"] == problem.problem_id
    assert module.verify({}, params, outputs, None) == []
    assert "never proof" in outputs["research_prompt"].lower()
