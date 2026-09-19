from __future__ import annotations

import json

import pytest

from cace_studio.build_lite import (
    BuildLiteError,
    BuildTask,
    load_build_lite_config,
    plan_build,
    task_fingerprint,
)


def _tasks():
    return {
        "lint": BuildTask(
            "lint",
            triggers=("src/**",),
            cache_inputs=("src/**",),
            estimated_seconds=1,
            fail_fast=True,
            cache_policy="skip_on_exact_hit",
        ),
        "unit": BuildTask(
            "unit",
            deps=("lint",),
            triggers=("src/**",),
            cache_inputs=("src/**", "tests/**"),
            estimated_seconds=5,
            cpu_units=2,
            cache_policy="skip_on_exact_hit",
        ),
        "web": BuildTask(
            "web",
            deps=("lint",),
            triggers=("web/**",),
            cache_inputs=("web/**",),
            estimated_seconds=4,
            cache_policy="skip_on_exact_hit",
        ),
        "formal": BuildTask(
            "formal",
            triggers=("formal/**",),
            cache_inputs=("formal/**",),
            estimated_seconds=9,
            proof_sensitive=True,
            cache_policy="restore_only",
        ),
    }


def test_changed_path_selects_dependency_closure(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_x(): pass\n", encoding="utf-8")
    plan = plan_build(
        _tasks(),
        repo_root=tmp_path,
        changed_paths=("src/a.py",),
        profile="quick",
        cpu_budget=2,
    )
    assert plan.selected_tasks == ("lint", "unit")
    assert plan.critical_path == ("lint", "unit")


def test_exact_cache_hit_can_skip_non_proof_task(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    task = _tasks()["lint"]
    fingerprint = task_fingerprint(tmp_path, task)
    plan = plan_build(
        _tasks(),
        repo_root=tmp_path,
        changed_paths=("src/a.py",),
        profile="quick",
        cache_state={"lint": fingerprint},
    )
    assert "lint" in plan.skipped_tasks
    unit_decision = next(item for item in plan.decisions if item.task_id == "unit")
    assert unit_decision.selected is True


def test_proof_sensitive_exact_cache_hit_never_skips_execution(tmp_path):
    (tmp_path / "formal").mkdir()
    (tmp_path / "formal" / "A.lean").write_text("theorem a : True := by trivial\n", encoding="utf-8")
    task = _tasks()["formal"]
    fingerprint = task_fingerprint(tmp_path, task)
    plan = plan_build(
        _tasks(),
        repo_root=tmp_path,
        changed_paths=("formal/A.lean",),
        profile="quick",
        cache_state={"formal": fingerprint},
    )
    assert "formal" not in plan.skipped_tasks
    decision = next(item for item in plan.decisions if item.task_id == "formal")
    assert "proof-sensitive-cache-restore-only" in decision.reasons


def test_independent_ready_tasks_share_parallel_batch(tmp_path):
    for directory in ("src", "web", "tests"):
        (tmp_path / directory).mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "web" / "x.js").write_text("1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("def test_x(): pass\n", encoding="utf-8")
    plan = plan_build(
        _tasks(),
        repo_root=tmp_path,
        changed_paths=("src/a.py", "web/x.js"),
        profile="quick",
        cpu_budget=4,
        max_parallel=4,
    )
    assert plan.batches[0].task_ids == ("lint",)
    assert set(plan.batches[1].task_ids) == {"unit", "web"}
    assert plan.scheduled_seconds < plan.serial_seconds


def test_cycle_fails_closed(tmp_path):
    config = {
        "schema": "cace.build-lite.v1",
        "tasks": [
            {"id": "a", "deps": ["b"]},
            {"id": "b", "deps": ["a"]},
        ],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(BuildLiteError, match="cycle"):
        load_build_lite_config(path)


def test_plan_explicitly_disclaims_proof_authority(tmp_path):
    plan = plan_build(
        _tasks(),
        repo_root=tmp_path,
        explicit_targets=("formal",),
        profile="quick",
    )
    assert "cannot replace canonical Lean qualification" in plan.note
