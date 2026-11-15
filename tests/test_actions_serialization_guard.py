from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "cace_actions_serialization_guard.py"
spec = importlib.util.spec_from_file_location("cace_actions_serialization_guard", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def run(run_id, name, status, sha="a" * 40):
    return {"id": run_id, "name": name, "status": status, "head_sha": sha, "html_url": f"https://example.invalid/{run_id}"}


def test_free_lane():
    assert mod.blockers([run(1, "CACE regression", "completed")]) == []


def test_queued_and_waiting_cace_runs_do_not_block_the_active_lane():
    runs = [
        run(1, "CACE canonical qualification", "queued"),
        run(2, "CACE collaboration validation", "waiting"),
        run(3, "CACE exact-pin preflight", "pending"),
        run(4, "CACE manual dispatch", "requested"),
    ]
    assert mod.blockers(runs) == []


def test_in_progress_cace_blocks():
    assert len(mod.blockers([run(2, "CACE regression", "in_progress")])) == 1


def test_non_cace_run_does_not_consume_cace_lane():
    assert mod.blockers([run(3, "Docs build", "queued")]) == []


def test_current_run_is_excluded():
    runs = [run(4, "CACE validation", "in_progress")]
    assert mod.blockers(runs, current_run_id=4) == []


def test_other_cace_run_still_blocks_when_current_excluded():
    runs = [run(4, "CACE validation", "in_progress"), run(5, "CACE formal", "in_progress")]
    found = mod.blockers(runs, current_run_id=4)
    assert [item["id"] for item in found] == [5]


def test_explicitly_ignored_cheap_workflow_does_not_block():
    runs = [
        run(6, "CACE Lean Source Sanity", "in_progress"),
        run(7, "CACE canonical qualification", "in_progress"),
    ]
    found = mod.blockers(
        runs,
        ignored_workflow_names={"CACE Lean Source Sanity"},
    )
    assert [item["id"] for item in found] == [7]


def test_ignore_name_is_exact_and_does_not_broaden_cace_lane():
    runs = [run(8, "CACE Lean Source Sanity extended", "in_progress")]
    found = mod.blockers(
        runs,
        ignored_workflow_names={"CACE Lean Source Sanity"},
    )
    assert [item["id"] for item in found] == [8]
