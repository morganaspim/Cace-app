from __future__ import annotations

import json

import pytest

from cace_studio.core.module import ExecutionContext
from cace_studio.modules.open_problems import OpenProblemModule
from cace_studio.research.open_problems import (
    OpenProblem,
    OpenProblemCatalog,
    default_open_problem_catalog,
)


def test_packaged_millennium_catalog_has_six_open_and_one_solved():
    catalog = default_open_problem_catalog()
    assert len(catalog.problems) == 7
    assert sum(problem.status == "open" for problem in catalog.problems) == 6
    solved = [problem for problem in catalog.problems if problem.status == "solved"]
    assert [problem.problem_id for problem in solved] == ["millennium.poincare"]
    assert all(problem.authority == "Clay Mathematics Institute" for problem in catalog.problems)
    assert all(problem.last_verified == "2026-09-19" for problem in catalog.problems)


def test_duplicate_problem_ids_fail_closed():
    problem = default_open_problem_catalog().problems[0]
    with pytest.raises(ValueError, match="duplicate problem_id"):
        OpenProblemCatalog(
            catalog_id="test.duplicate",
            title="Duplicate",
            authority="Test",
            last_verified="2026-09-19",
            problems=(problem, problem),
        )


def test_invalid_status_fails_closed():
    raw = default_open_problem_catalog().problems[0].to_dict(include_hash=False)
    raw["status"] = "definitely-solved-by-ai"
    with pytest.raises(ValueError, match="unsupported"):
        OpenProblem.from_mapping(raw)


def test_custom_catalog_rejects_unknown_fields():
    payload = json.loads(
        """{
          "schema":"cace.open-problem-catalog.v1",
          "catalog_id":"custom.test",
          "title":"Custom",
          "authority":"User",
          "last_verified":"2026-09-19",
          "problems":[],
          "execute_code":"no"
        }"""
    )
    with pytest.raises(ValueError, match="unsupported catalog fields"):
        OpenProblemCatalog.from_mapping(payload)


def test_play_context_preserves_open_problem_nonclaim():
    problem = default_open_problem_catalog().by_id("millennium.riemann")
    context = problem.play_context()
    assert "marked OPEN" in context
    assert "does not mean it has been solved" in context
    assert "Distinguish heuristic/numerical evidence from proof" in context


def test_open_problem_module_generates_no_verification_evidence():
    problem = default_open_problem_catalog().by_id("millennium.navier-stokes")
    module = OpenProblemModule()
    params = problem.to_module_params()
    module.validate({}, params)
    outputs = module.execute({}, params, ExecutionContext(run_id="test", seed=0))
    assert outputs["problem"]["problem_id"] == problem.problem_id
    assert "Research navigation only" in outputs["research_prompt"]
    assert module.verify({}, params, outputs, ExecutionContext(run_id="test", seed=0)) == []


def test_semantic_hash_changes_when_status_snapshot_changes():
    original = default_open_problem_catalog().problems[0]
    changed = OpenProblem(
        problem_id=original.problem_id,
        title=original.title,
        domain=original.domain,
        status="solved",
        collection=original.collection,
        summary=original.summary,
        authority=original.authority,
        source_url=original.source_url,
        last_verified="2026-09-20",
        tags=original.tags,
    )
    assert original.semantic_sha256 != changed.semantic_sha256
