from merlin_lms.planner import plan_next_tasks
import pytest


def learner():
    return {
        "pathway_weights": {"mathematician": 0.6, "mathematics_programmer": 0.3,
                            "computational_problem_solver": 0.1},
        "interests": ["number_theory", "python"],
        "concept_states": [
            {"concept_id": "fractions", "state": "mastered", "evidence_refs": ["ev-1"]},
            {"concept_id": "variables", "state": "practicing", "evidence_refs": ["ev-2"]},
        ],
    }


def tasks():
    return [
        {"task_id": "proof-001", "concept_id": "prime-proof", "requires": ["fractions"],
         "pathways": {"mathematician": 1.0}, "interest_tags": ["number_theory"],
         "learning_value": 0.9, "transfer_value": 0.9, "estimated_minutes": 25},
        {"task_id": "code-001", "concept_id": "python-loops", "requires": ["variables"],
         "pathways": {"mathematics_programmer": 1.0}, "interest_tags": ["python"],
         "learning_value": 0.8, "transfer_value": 0.7, "estimated_minutes": 15},
        {"task_id": "blocked-001", "concept_id": "calculus", "requires": ["limits"],
         "pathways": {"mathematician": 1.0}, "interest_tags": [],
         "learning_value": 1.0, "transfer_value": 1.0, "estimated_minutes": 30},
    ]


def test_ranks_eligible_tasks_and_explains_recommendations():
    result = plan_next_tasks(learner(), tasks(), max_minutes=30)
    assert result["eligible_count"] == 2
    assert result["ranked_tasks"][0]["task_id"] == "proof-001"
    assert "matches_selected_pathways" in result["ranked_tasks"][0]["reason_codes"]
    assert result["blocked_tasks"] == [{"task_id": "blocked-001",
        "blocked_reason": "prerequisites_not_yet_demonstrated", "missing_prerequisites": ["limits"]}]


def test_is_deterministic_and_tie_breaks_by_task_id():
    fixture = learner()
    fixture["pathway_weights"] = {"mathematician": 1.0, "mathematics_programmer": 0.0,
                                  "computational_problem_solver": 0.0}
    pair = [{"task_id": name, "concept_id": name, "requires": [],
             "pathways": {"mathematician": 1.0}, "learning_value": 0.5,
             "transfer_value": 0.5, "estimated_minutes": 20} for name in ["z-task", "a-task"]]
    assert plan_next_tasks(fixture, pair) == plan_next_tasks(fixture, pair)
    assert [x["task_id"] for x in plan_next_tasks(fixture, pair)["ranked_tasks"]] == ["a-task", "z-task"]


def test_excludes_completed_and_over_budget_tasks():
    result = plan_next_tasks(learner(), tasks(), max_minutes=20, completed_task_ids=["code-001"])
    assert result["ranked_tasks"] == []
    assert {x["task_id"]: x["blocked_reason"] for x in result["blocked_tasks"]} == {
        "proof-001": "exceeds_time_budget", "blocked-001": "exceeds_time_budget"}


def test_requires_at_least_one_pathway_weight():
    fixture = learner()
    fixture["pathway_weights"] = {key: 0.0 for key in ("mathematician", "mathematics_programmer", "computational_problem_solver")}
    with pytest.raises(ValueError, match="at least one pathway"):
        plan_next_tasks(fixture, tasks())


def test_rejects_duplicate_task_ids():
    fixture = tasks()
    fixture.append(dict(fixture[0]))
    with pytest.raises(ValueError, match="duplicate task_id"):
        plan_next_tasks(learner(), fixture)


def test_provisional_prerequisite_is_accepted():
    fixture = learner()
    fixture["concept_states"][1]["state"] = "provisional"
    result = plan_next_tasks(fixture, tasks())
    assert "code-001" in [x["task_id"] for x in result["ranked_tasks"]]
